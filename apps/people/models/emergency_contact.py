import reversion
from django.conf import settings
from django.db import models
from django.utils.translation import gettext
from django.utils.translation import ugettext_lazy as _
from phonenumber_field.modelfields import PhoneNumberField


@reversion.register(fields=('user',), follow=('user',))
class EmergencyContact(models.Model):
    """Contact information a person to be notified in an emergency involving the associated user."""

    MIN_PER_USER = 1
    MAX_PER_USER = 3

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='emergency_contacts')
    contact_name = models.CharField(max_length=100, verbose_name=_('Name of contact'))
    relation = models.CharField(max_length=100, verbose_name=_('Relation to contact'), blank=True,
                                help_text=_('Optional. For example: parent, partner, friend, etc.'))
    phone_number = PhoneNumberField(verbose_name=_('Phone number of contact'))
    remarks = models.CharField(max_length=200, verbose_name=_('Remarks'), blank=True)

    def __str__(self):
        return gettext('Emergency contact of user %(user)s') % {'user': self.user}

    class Meta:
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')
