from pathlib import Path
import asyncio
from agentics_lundmj.agent import Agent
from agentics_lundmj.tool_box import ToolBox
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.views.generic import ListView
from asgiref.sync import sync_to_async
import uuid
from .models import Message, MessageScorecard

PROMPTS_PATH = Path(__file__).resolve().parent / "prompts"

class InitiateLead(View):
    async def get(self, request, *args, **kwargs):
        # Use sync_to_async to call Django's render from an async view.
        return await sync_to_async(render)(request, 'messaging/create_lead.html')

    async def post(self, request, *args, **kwargs):
        # If a lead_message is supplied via the form use it, otherwise
        # call the agent in a thread so we don't block the event loop.
        lead_message = request.POST.get('lead_message', '').strip()

        if not lead_message:
            def call_agent():
                shopper = Agent(
                    PROMPTS_PATH / "property_shopper.md",
                    history_limit=1,
                    model_name='gpt-4.1',
                )
                return shopper.chat_once("Media: Email\n")

            lead_message = await asyncio.to_thread(call_agent)

        try:
            # run ORM creation in a thread
            def create_message():
                return Message.objects.create(
                    type=Message.EMAIL,
                    lead_message=lead_message,
                )

            message = await asyncio.to_thread(create_message)
        except Exception as e:
            return HttpResponse(status=500, content=str(e))

        # On success, render a tiny confirmation page showing the created id
        return await sync_to_async(render)(request, 'messaging/create_lead_success.html', {
            'message': message,
            'message_id': message.id,
        }, status=201)


class MessageList(ListView):
    model = Message
    template_name = 'messaging/message_list.html'
    context_object_name = 'messages'
    queryset = Message.objects.exclude(
        response_message__isnull=False
    ).order_by('-lead_datetime')


class ReplyView(View):
    @staticmethod
    def generate_report_with_id(
        message_id: uuid.UUID,
        platform_score: int,
        platform_rationale: str,
        question_score: int,
        question_rationale: str,
        professionalism_score: int,
        professionalism_rationale: str,
        personalization_score: int,
        personalization_rationale: str,
        legal_score: int,
        legal_rationale: str,
        actionability_score: int,
        actionability_rationale: str,
    ) -> None:
        scorecard = MessageScorecard.objects.create(
            platform_score=platform_score,
            question_score=question_score,
            professionalism_score=professionalism_score,
            personalization_score=personalization_score,
            legal_score=legal_score,
            actionability_score=actionability_score,

            platform_rationale=platform_rationale,
            question_rationale=question_rationale,
            professionalism_rationale=professionalism_rationale,
            personalization_rationale=personalization_rationale,
            legal_rationale=legal_rationale,
            actionability_rationale=actionability_rationale,
        )
        associated_message = Message.objects.get(id=message_id)
        associated_message.scorecard = scorecard
        associated_message.save()

    async def grade_response(message_id: uuid.UUID, response_message: str):
        grade_toolbox = ToolBox()
        @grade_toolbox.tool
        def generate_report(
            platform_score: int,
            platform_rationale: str,
            question_score: int,
            question_rationale: str,
            professionalism_score: int,
            professionalism_rationale: str,
            personalization_score: int,
            personalization_rationale: str,
            legal_score: int,
            legal_rationale: str,
            actionability_score: int,
            actionability_rationale: str,
        ) -> str:
            """
            Create a grade report for a reply from a leasing agent.
            Scores range between 1-10, inclusive.

            platform: How appropriate the reply is for the platform
            question: How well the reply answers the questions asked
            professionalism: How professional the reply is
            personalization: How personalized the reply is
            legal: The degree to which the reply follows legal guidelines
            actionability: How actionable the reply is

            Returns whether the report successfully generated.
            """
            scores = [
                platform_score,
                question_score,
                professionalism_score,
                personalization_score,
                legal_score,
                actionability_score,
            ]
            rationales = [
                platform_rationale,
                question_rationale,
                professionalism_rationale,
                personalization_rationale,
                legal_rationale,
                actionability_rationale,
            ]
            if not all(1 <= score <= 10 for score in scores):
                return "Failure: All scores must be between 1 and 10."
            if not all(rationale.strip() for rationale in rationales):
                return "Failure: All rationales must be provided."

            ReplyView.generate_report_with_id(
                message_id,
                platform_score,
                platform_rationale,
                question_score,
                question_rationale,
                professionalism_score,
                professionalism_rationale,
                personalization_score,
                personalization_rationale,
                legal_score,
                legal_rationale,
                actionability_score,
                actionability_rationale,
            )
            return "Success: Grade report generated."

        def run_grader():
            grader = Agent(
                PROMPTS_PATH / "response_grader.md",
                history_limit=2,
                model_name='gpt-4o',
                tool_box=grade_toolbox,
            )
            prompt = f"""
            Lead Message: {Message.objects.get(id=message_id).lead_message}
            Platform: {Message.objects.get(id=message_id).type}
            Response Message: {response_message}
            """
            grader.chat_once(prompt)
            return ReplyView.scorecard_id

        scorecard_id = await asyncio.to_thread(run_grader)
        print(f"Grading complete for message {message_id}, scorecard {scorecard_id}")

        if scorecard_id:
            def attach_scorecard():
                msg = Message.objects.get(id=message_id)
                msg.scorecard = MessageScorecard.objects.get(id=scorecard_id)
                msg.save()

            await asyncio.to_thread(attach_scorecard)

    async def post(self, request: HttpRequest, pk, *args, **kwargs):
        # fetch message in a thread (ORM)
        message = await asyncio.to_thread(lambda: get_object_or_404(Message, id=pk))
        response_message = request.POST.get('response_message', '').strip()
        if not response_message:
            return HttpResponse('response_message required', status=400)

        try:
            await asyncio.to_thread(message.log_response, response_message)
        except Exception as e:
            return HttpResponse(status=500, content=str(e))

        # Start background grading coroutine and return immediately.
        asyncio.create_task(ReplyView.grade_response(message.id, response_message))

        return redirect('messaging:list')
