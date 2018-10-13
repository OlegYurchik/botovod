from botovod.extensions.djangoapp.botovod import manager
from botovod.extensions.djangoapp.botovod.models import Bot
from django.core.management.base import BaseCommand
import json



class Command(BaseCommand):
    help = "Init bots"

    def handle(self, *args, **options):
        bots = []
        if not args:
            bots = Bot.objects.all()
        for name in args:
            bot = Bot.objects.get(name=name)
            bots.append(bot)
        for bot in bots:
            manager.add_agent(name=bot.name, agent=bot.agent, settings=json.loads(bot.settings))
