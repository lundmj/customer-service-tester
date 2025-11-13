from datetime import datetime
import uuid
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator


## Custom Fields ##

class ScoreField(models.IntegerField):
    def __init__(self, *args, **kwargs):
        # Merge any validators passed in by callers with the ScoreField defaults.
        existing_validators = kwargs.pop('validators', []) or []
        validators = list(existing_validators) + [
            MinValueValidator(1), MaxValueValidator(10)
        ]
        kwargs['validators'] = validators
        super().__init__(*args, **kwargs)

    def __str__(self):
        # Fields don't carry instance values; keep a simple repr.
        return "ScoreField(1..10)"


## Models ##

class Message(models.Model):
    FACEBOOK = 'FACEBOOK'
    EMAIL = 'EMAIL'
    SMS = 'SMS'
    MESSAGE_TYPES = [
        (FACEBOOK, 'Facebook'),
        (EMAIL, 'Email'),
        (SMS, 'SMS'),
    ]

    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
    )
    type = models.CharField(
        max_length=20,
        choices=MESSAGE_TYPES,
        default=EMAIL,
    )
    lead_message = models.TextField()
    lead_datetime = models.DateTimeField(auto_now_add=True)
    response_message = models.TextField(blank=True, null=True)
    response_datetime = models.DateTimeField(blank=True, null=True)
    scorecard = models.OneToOneField(
        'MessageScorecard',
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name='message',
    )

    def log_response(self, response_message):
        self.response_message = response_message
        self.response_datetime = datetime.now()
        self.save()


class MessageScorecard(models.Model):
    platform_score = ScoreField()
    question_score = ScoreField()
    professionalism_score = ScoreField()
    personalization_score = ScoreField()
    legal_score = ScoreField()
    actionability_score = ScoreField()

    platform_rationale = models.TextField()
    question_rationale = models.TextField()
    professionalism_rationale = models.TextField()
    personalization_rationale = models.TextField()
    legal_rationale = models.TextField()
    actionability_rationale = models.TextField()

    @property
    def overall_score(self):
        """Return the average of the six score fields as a float.

        This keeps the property simple and avoids division-by-zero because
        all score fields are required integers.
        """
        scores = [
            self.platform_score,
            self.question_score,
            self.professionalism_score,
            self.personalization_score,
            self.legal_score,
            self.actionability_score,
        ]
        if None in scores:
            raise ValueError("All score fields must be set to compute overall_score.")
        return sum(scores) / len(scores)

    class Meta:
        constraints = [
            models.CheckConstraint(
                check=models.Q(platform_score__gte=1, platform_score__lte=10),
                name='platform_score_range',
            ),
            models.CheckConstraint(
                check=models.Q(question_score__gte=1, question_score__lte=10),
                name='question_score_range',
            ),
            models.CheckConstraint(
                check=models.Q(professionalism_score__gte=1, professionalism_score__lte=10),
                name='professionalism_score_range',
            ),
            models.CheckConstraint(
                check=models.Q(personalization_score__gte=1, personalization_score__lte=10),
                name='personalization_score_range',
            ),
            models.CheckConstraint(
                check=models.Q(legal_score__gte=1, legal_score__lte=10),
                name='legal_score_range',
            ),
            models.CheckConstraint(
                check=models.Q(actionability_score__gte=1, actionability_score__lte=10),
                name='actionability_score_range',
            ),
        ]
        
    