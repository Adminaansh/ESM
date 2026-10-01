import random
import uuid

from django.db import models
from studio.models import JobObject

class Chain(models.Model):
    chain_guid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    chain_code = models.PositiveIntegerField(unique=True, null=True, blank=True)
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def _generate_chain_code(self):
        code = random.randint(100000, 999999)
        while Chain.objects.filter(chain_code=code).exists():
            code = random.randint(100000, 999999)
        return code

    def save(self, *args, **kwargs):
        if not self.chain_code:
            self.chain_code = self._generate_chain_code()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

class ChainNode(models.Model):
    chain = models.ForeignKey(Chain, related_name='nodes', on_delete=models.CASCADE)
    job = models.ForeignKey(JobObject, on_delete=models.CASCADE)
    target = models.ForeignKey(
        'infrastructure.InfrastructureTarget',
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='chain_nodes'
    )
    # Metadata for UI positioning in the graph
    pos_x = models.FloatField(default=0)
    pos_y = models.FloatField(default=0)


class ChainEdge(models.Model):
    CONDITION_CHOICES = [
        ('SUCCESS', 'On Success'),
        ('FAILURE', 'On Failure'),
        ('ANY', 'Always'),
    ]
    chain = models.ForeignKey(Chain, related_name='edges', on_delete=models.CASCADE)
    source = models.ForeignKey(ChainNode, related_name='outgoing', on_delete=models.CASCADE)
    target = models.ForeignKey(ChainNode, related_name='incoming', on_delete=models.CASCADE)
    condition = models.CharField(max_length=10, choices=CONDITION_CHOICES, default='SUCCESS')


