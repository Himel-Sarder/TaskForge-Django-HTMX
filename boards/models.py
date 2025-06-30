from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.conf import settings

class Board(models.Model):
    name = models.CharField(max_length=100)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='boards',
        default=1  # Set to ID of your first user
    )
    members = models.ManyToManyField(User, related_name='shared_boards', blank=True)

    def __str__(self):
        return self.name

    def has_access(self, user):
        return user == self.owner or user in self.members.all()

class List(models.Model):
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='lists')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"{self.name} ({self.board.name})"

class Task(models.Model):
    list = models.ForeignKey(List, on_delete=models.CASCADE, related_name="tasks")
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    is_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    due_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='created_tasks')

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.title

    @property
    def is_overdue(self):
        return (
            not self.is_completed and
            self.due_date and
            self.due_date < timezone.now().date()
        )