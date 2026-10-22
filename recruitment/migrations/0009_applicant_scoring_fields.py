from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("recruitment", "0008_alter_candidate_table_alter_candidatedocument_table_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="recruitment",
            name="applicant_skill_score_weight",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text="Share of the total score from resume skill matching (with survey weight).",
                verbose_name="Applicant skill score weight (%)",
            ),
        ),
        migrations.AddField(
            model_name="recruitment",
            name="applicant_survey_score_weight",
            field=models.PositiveSmallIntegerField(
                default=50,
                help_text="Share of the total score from preferred survey answers (with skill weight).",
                verbose_name="Applicant survey score weight (%)",
            ),
        ),
        migrations.AddField(
            model_name="recruitmentsurvey",
            name="preferred_answers",
            field=models.TextField(
                blank=True,
                help_text="Score applicants against this question. Choices / Yes-No: separate with ',  '. Text: keywords with | between them. Number / Rating / %: exact value, range (e.g. 3-5), or >= / <= / > / <. Leave blank to ignore in scoring.",
                null=True,
                verbose_name="Preferred answers (scoring)",
            ),
        ),
        migrations.AddField(
            model_name="recruitmentsurvey",
            name="scoring_weight",
            field=models.PositiveSmallIntegerField(
                default=1,
                help_text="Relative importance when combining survey questions.",
                verbose_name="Scoring weight",
            ),
        ),
    ]
