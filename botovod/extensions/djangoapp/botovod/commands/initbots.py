from botovod.extensions.djangoapp.botovod import manager
from botovod.extensions.djangoapp.botovod.models import Bot
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Init bots"

    def handle(self, *args, **options):
        manager.add_handler(start)
        manager.add_handler(today)
        manager.add_handler(tomorrow)
        manager.add_handler(after_tomorrow)
        manager.add_handler(date)
        manager.add_handler(bite)
        manager.add_handler(unknown)
        
        bots = []
        if not args:
            bots = Bot.objects.all()
        for name in args:
            bot = Bot.objects.get(name=name)
            bots.append(bot)
        for bot in bots:
            manager.add_agent(name=bot.name, agent=bot.agent, settings=json.loads(bot.settings))
