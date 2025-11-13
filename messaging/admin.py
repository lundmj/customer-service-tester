from django.contrib import admin

from .models import Message, MessageScorecard


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ('id', 'type', 'lead_datetime', 'response_datetime', 'get_score')
    readonly_fields = ('id',)
    search_fields = ('type', 'lead_message', 'response_message')
    list_filter = ('type',)

    def get_score(self, obj):
        if obj.scorecard:
            try:
                return f"{obj.scorecard.overall_score:.1f}/10"
            except Exception:
                return "-"
        return "-"
    get_score.short_description = 'Score'


@admin.register(MessageScorecard)
class MessageScorecardAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'platform_score',
        'question_score',
        'professionalism_score',
        'personalization_score',
        'legal_score',
        'actionability_score',
        'overall_score_display',
    )
    readonly_fields = ('overall_score_display',)

    def overall_score_display(self, obj):
        # Use the model property to compute the average; return nicely formatted
        try:
            score = obj.overall_score
        except Exception:
            return None
        if score is None:
            return None
        return f"{score:.2f}"

    overall_score_display.short_description = 'Overall score'
