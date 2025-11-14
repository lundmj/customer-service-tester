from pathlib import Path
from agentics_lundmj.agent import Agent
from agentics_lundmj.tool_box import ToolBox
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from .models import Message, MessageScorecard

PROMPTS_PATH = Path(__file__).resolve().parent / "prompts"

class InitiateLead(View):
    def get(self, request, *args, **kwargs):
        return render(request, 'messaging/create_lead.html')

    def post(self, request, *args, **kwargs):
        shopper = Agent(
            PROMPTS_PATH / "property_shopper.md",
            history_limit=1,
            model_name='gpt-4.1',
        )
        lead_message = shopper.chat_once(
            "Media: Email\n"
        )

        try:
            message = Message.objects.create(
                type=Message.EMAIL,
                lead_message=lead_message,
            )
        except Exception as e:
            return HttpResponse(status=500, content=str(e))

        # On success, render a tiny confirmation page showing the created id
        return render(request, 'messaging/create_lead_success.html', {
            'message': message,
            'message_id': message.id,
        }, status=201)


class MessageList(View):
    def get(self, request, *args, **kwargs):
        """Show a list of created Message rows with a reply form for each."""
        messages = Message.objects.exclude(
            response_message__isnull=False
        ).order_by('-lead_datetime')
        return render(request, 'messaging/message_list.html', {
            'messages': messages,
        })


class ReplyView(View):
    scorecard_id = None

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
        Create a grade report for a reply from a leasing agent. Scores range between 1-5.

        platform: How appropriate the reply is for the platform (email vs. facebook)
        question: How well the reply answers the questions asked
        professionalism: How professional the reply is
        personalization: How personalized the reply is
        legal: The degree to which the reply follows legal guidelines
        actionability: How actionable the reply is

        Returns whether the report successfully generated.
        """
        if not all(
            1 <= score <= 5 for score in [
                platform_score,
                question_score,
                professionalism_score,
                personalization_score,
                legal_score,
                actionability_score,
            ]
        ):
            return "Failure: All scores must be between 1 and 5."
        if not all(
            rationale.strip() for rationale in [
                platform_rationale,
                question_rationale,
                professionalism_rationale,
                personalization_rationale,
                legal_rationale,
                actionability_rationale,
            ]
        ):
            return "Failure: All rationales must be provided."

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
        ReplyView.scorecard_id = scorecard.id
        return "Success: Grade report generated."

    def grade_response(message_obj: Message, response_message: str):
        grader = Agent(
            PROMPTS_PATH / "response_grader.md",
            history_limit=2,
            model_name='gpt-4o',
            tool_box=ReplyView.grade_toolbox
        )
        prompt = f"""
        Lead Message: {message_obj.lead_message}
        Platform: {message_obj.type}
        Response Message: {response_message}
        """
        grader.chat_once(prompt)
        print('ReplyView.scorecard_id:', ReplyView.scorecard_id)
        message_obj.scorecard_id = ReplyView.scorecard_id
        message_obj.save()

    def post(self, request: HttpRequest, pk, *args, **kwargs):
        message = get_object_or_404(Message, id=pk)
        response_message = request.POST.get('response_message', '').strip()
        if not response_message:
            return HttpResponse('response_message required', status=400)

        try:
            message.log_response(response_message)
        except Exception as e:
            return HttpResponse(status=500, content=str(e))

        ReplyView.grade_response(message, response_message)

        return redirect('messaging:list')
