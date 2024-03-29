# -*- coding: utf-8 -*-


from django.db import migrations, models
import django.core.validators
import sa_api_v2.models.profiles


class Migration(migrations.Migration):

    dependencies = [
        ("sa_api_v2", "0008_attachment_visible"),
    ]

    operations = [
        migrations.AlterModelManagers(
            name="user",
            managers=[("objects", sa_api_v2.models.profiles.ShareaboutsUserManager()),],
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="bcc_email_1",
            field=models.EmailField(
                default=None, max_length=254, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="bcc_email_2",
            field=models.EmailField(
                default=None, max_length=254, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="bcc_email_3",
            field=models.EmailField(
                default=None, max_length=254, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="bcc_email_4",
            field=models.EmailField(
                default=None, max_length=254, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="bcc_email_5",
            field=models.EmailField(
                default=None, max_length=254, null=True, blank=True
            ),
        ),
        migrations.AlterField(
            model_name="placeemailtemplate",
            name="from_email",
            field=models.EmailField(max_length=254),
        ),
        migrations.AlterField(
            model_name="user",
            name="email",
            field=models.EmailField(
                max_length=254, verbose_name="email address", blank=True
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="groups",
            field=models.ManyToManyField(
                related_query_name="user",
                related_name="user_set",
                to="auth.Group",
                blank=True,
                help_text="The groups this user belongs to. A user will get all permissions granted to each of their groups.",
                verbose_name="groups",
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="last_login",
            field=models.DateTimeField(
                null=True, verbose_name="last login", blank=True
            ),
        ),
        migrations.AlterField(
            model_name="user",
            name="username",
            field=models.CharField(
                error_messages={"unique": "A user with that username already exists."},
                max_length=30,
                validators=[
                    django.core.validators.RegexValidator(
                        "^[\\w.@+-]+$",
                        "Enter a valid username. This value may contain only letters, numbers and @/./+/-/_ characters.",
                        "invalid",
                    )
                ],
                help_text="Required. 30 characters or fewer. Letters, digits and @/./+/-/_ only.",
                unique=True,
                verbose_name="username",
            ),
        ),
    ]
