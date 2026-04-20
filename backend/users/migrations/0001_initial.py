from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True
    dependencies = []

    operations = [
        migrations.CreateModel(
            name='User',
            fields=[
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('email', models.EmailField(db_index=True, max_length=254, unique=True)),
                ('first_name', models.CharField(blank=True, max_length=100)),
                ('last_name', models.CharField(blank=True, max_length=100)),
                ('avatar', models.ImageField(blank=True, null=True, upload_to='avatars/')),
                ('bio', models.TextField(blank=True, max_length=500)),
                ('role', models.CharField(choices=[('user', 'User'), ('admin', 'Admin'), ('superadmin', 'Super Admin')], db_index=True, default='user', max_length=20)),
                ('status', models.CharField(choices=[('active', 'Active'), ('suspended', 'Suspended'), ('deleted', 'Deleted')], default='active', max_length=20)),
                ('is_active', models.BooleanField(default=True)),
                ('is_staff', models.BooleanField(default=False)),
                ('is_superuser', models.BooleanField(default=False)),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('is_mock_data', models.BooleanField(default=False)),
                ('admin_note', models.TextField(blank=True)),
                ('suspension_reason', models.TextField(blank=True)),
                ('suspended_at', models.DateTimeField(blank=True, null=True)),
                ('suspended_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='suspended_users', to='users.user')),
            ],
            options={'db_table': 'sp_users', 'ordering': ['-date_joined']},
        ),
        migrations.CreateModel(
            name='UserPreference',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('favorite_categories', models.JSONField(blank=True, default=list)),
                ('preferred_language', models.CharField(default='English', max_length=50)),
                ('email_notifications', models.BooleanField(default=True)),
                ('due_date_reminders', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='preferences', to='users.user')),
            ],
            options={'db_table': 'sp_user_preferences'},
        ),
    ]
