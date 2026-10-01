from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from studio.models import JobObject, ScriptRevision, PromptSet


class Command(BaseCommand):
    help = 'Create a sample job that fetches Pune weather using a public weather endpoint.'

    def handle(self, *args, **options):
        User = get_user_model()
        user = User.objects.first()
        if user is None:
            self.stderr.write('No user exists in the database. Create a user first.')
            return

        job_name = 'PUNE_WEATHER_FETCH'
        if JobObject.objects.filter(name=job_name).exists():
            self.stdout.write(f'Job "{job_name}" already exists.')
            return

        job = JobObject.objects.create(
            name=job_name,
            title='Fetch current weather for Pune',
            platform='UNIX',
            is_active=True,
            active_revision=1,
            tags=['weather', 'pune', 'api'],
            owner=user,
        )

        script_content = '''import json
import urllib.request


def fetch_pune_weather():
    url = "https://wttr.in/Pune?format=j1"
    headers = {"User-Agent": "ESM Weather Job/1.0"}
    request = urllib.request.Request(url, headers=headers)

    with urllib.request.urlopen(request, timeout=15) as response:
        data = json.load(response)

    current = data.get('current_condition', [{}])[0]
    temp_c = current.get('temp_C', 'N/A')
    desc = current.get('weatherDesc', [{}])[0].get('value', 'N/A')
    humidity = current.get('humidity', 'N/A')

    print(f'Pune weather: {desc}, {temp_c}°C, Humidity {humidity}%')


if __name__ == '__main__':
    fetch_pune_weather()
'''

        ScriptRevision.objects.create(
            job_object=job,
            version=1,
            content=script_content,
            created_by=user,
        )

        PromptSet.objects.create(
            job_object=job,
            variable_name='&LOCATION#',
            label='City',
            field_type='text',
            default_value='Pune',
        )

        self.stdout.write(self.style.SUCCESS(f'Created job "{job_name}" with Pune weather fetch logic.'))
