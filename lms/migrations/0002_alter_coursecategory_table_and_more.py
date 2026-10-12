# Generated for DB_TABLE_PREFIX (dsg_hr_)

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("lms", "0001_initial"),
    ]

    operations = [
        migrations.AlterModelTable(
            name="coursecategory",
            table="dsg_hr_lms_coursecategory",
        ),
        migrations.AlterModelTable(
            name="course",
            table="dsg_hr_lms_course",
        ),
        migrations.AlterModelTable(
            name="coursemodule",
            table="dsg_hr_lms_coursemodule",
        ),
        migrations.AlterModelTable(
            name="lesson",
            table="dsg_hr_lms_lesson",
        ),
        migrations.AlterModelTable(
            name="courseenrollment",
            table="dsg_hr_lms_courseenrollment",
        ),
        migrations.AlterModelTable(
            name="lessonprogress",
            table="dsg_hr_lms_lessonprogress",
        ),
    ]
