from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save

from .utilities import get_timestamp_path, send_new_comment_notification


class AdvUser(AbstractUser):
    is_activated = models.BooleanField(default=True, db_index=True, verbose_name='Activated?')
    send_messages = models.BooleanField(default=True, verbose_name='Send notifications about new comments?')

    def delete(self, *args, **kwargs):
        for bb in self.bb_set.all():
            bb.delete()
        super().delete(*args, **kwargs)

    class Meta(AbstractUser.Meta):
        pass


class Rubric(models.Model):
    name = models.CharField(max_length=20, db_index=True, unique=True,
                            verbose_name='Name')
    order = models.SmallIntegerField(default=0, db_index=True, verbose_name='Order')
    super_rubric = models.ForeignKey('SuperRubric', on_delete=models.PROTECT,
                                     null=True, blank=True, verbose_name='Super rubric')


class SuperRubricManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=True)


class SuperRubric(Rubric):
    objects = SuperRubricManager()

    def __str__(self):
        return self.name

    class Meta:
        proxy = True
        ordering = ('order', 'name')
        verbose_name = 'Super rubric'
        verbose_name_plural = 'Super rubrics'


class SubRubricManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(super_rubric__isnull=False)


class SubRubric(Rubric):
    objects = SubRubricManager()

    def __str__(self):
        return '%s - %s' % (self.super_rubric.name, self.name)

    class Meta:
        proxy = True
        ordering = ('super_rubric__order', 'super_rubric__name', 'order',
                    'name')
        verbose_name = 'Sub rubric'
        verbose_name_plural = 'Sub rubrics'


class Bb(models.Model):
    rubric = models.ForeignKey(SubRubric, on_delete=models.PROTECT, verbose_name='Rubric')
    title = models.CharField(max_length=40, verbose_name='Product')
    content = models.TextField(verbose_name='Description')
    price = models.FloatField(default=0, verbose_name='Price')
    contacts = models.TextField(verbose_name='Contacts')
    image = models.ImageField(blank=True, upload_to=get_timestamp_path, verbose_name='Image')
    author = models.ForeignKey(AdvUser, on_delete=models.CASCADE, verbose_name='Author')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Active?')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Published')

    def delete(self, *args, **kwargs):
        for ai in self.additionalimage_set.all():
            ai.delete()
        super().delete(*args, **kwargs)

    class Meta:
        verbose_name_plural = 'Ads'
        verbose_name = 'Ad'
        ordering = ['-created_at']


class AdditionalImage(models.Model):
    bb = models.ForeignKey(Bb, on_delete=models.CASCADE, verbose_name='Ad')
    image = models.ImageField(upload_to=get_timestamp_path, verbose_name='Image')

    class Meta:
        verbose_name_plural = 'Additional images'
        verbose_name = 'Additional image'


class Comment(models.Model):
    bb = models.ForeignKey(Bb, on_delete=models.CASCADE, verbose_name='Ad')
    author = models.CharField(max_length=30, verbose_name='Author')
    content = models.TextField(verbose_name='Text')
    is_active = models.BooleanField(default=True, db_index=True, verbose_name='Display?')
    created_at = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='Published')

    class Meta:
        verbose_name_plural = 'Comments'
        verbose_name = 'Comment'
        ordering = ['created_at']


def post_save_dispatcher(sender, **kwargs):
    author = kwargs['instance'].bb.author
    if kwargs['created'] and author.send_messages:
        send_new_comment_notification(kwargs['instance'])


post_save.connect(post_save_dispatcher, sender=Comment)
