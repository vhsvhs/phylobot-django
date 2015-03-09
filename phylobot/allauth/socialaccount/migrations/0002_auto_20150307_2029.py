# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('socialaccount', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='socialaccount',
            name='provider',
            field=models.CharField(max_length=30, verbose_name='provider', choices=[(b'openid', b'OpenID'), (b'linkedin_oauth2', b'LinkedIn'), (b'facebook', b'Facebook'), (b'linkedin', b'LinkedIn'), (b'github', b'GitHub')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='socialapp',
            name='provider',
            field=models.CharField(max_length=30, verbose_name='provider', choices=[(b'openid', b'OpenID'), (b'linkedin_oauth2', b'LinkedIn'), (b'facebook', b'Facebook'), (b'linkedin', b'LinkedIn'), (b'github', b'GitHub')]),
            preserve_default=True,
        ),
        migrations.AlterField(
            model_name='socialtoken',
            name='token',
            field=models.TextField(help_text='"oauth_token" (OAuth1) or access token (OAuth2)', verbose_name='token'),
            preserve_default=True,
        ),
    ]
