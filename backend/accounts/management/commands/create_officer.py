from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

User = get_user_model()


class Command(BaseCommand):
    help = "Create an officer user (mediator / court clerk / arbitrator)."

    def add_arguments(self, parser):
        parser.add_argument("--username", required=True)
        parser.add_argument("--password", required=True)
        parser.add_argument("--email", default="")

    def handle(self, *args, **options):
        username = options["username"]
        password = options["password"]
        email = options["email"]

        if User.objects.filter(username=username).exists():
            self.stdout.write(self.style.WARNING(f"User '{username}' already exists."))
            return

        user = User.objects.create_user(
            username=username,
            password=password,
            email=email,
            role=User.Role.OFFICER,
        )
        self.stdout.write(self.style.SUCCESS(
            f"Officer created: {user.username} (id={user.id})"
        ))