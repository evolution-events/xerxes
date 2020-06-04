# from django.shortcuts import render
import reversion
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import ValidationError
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse
from django.utils.functional import cached_property
from django.utils.translation import gettext as _
from django.views.generic import DetailView, View
from django.views.generic.base import ContextMixin, TemplateResponseMixin
from django.views.generic.edit import FormView

from apps.events.models import Event
from apps.people.models import Address, ArtaUser, MedicalDetails

from .forms import (EmergencyContactFormSet, FinalCheckForm, MedicalDetailForm, PersonalDetailForm,
                    RegistrationOptionsForm)
from .models import Registration
from .services import RegistrationNotifyService, RegistrationStatusService


class RegistrationStartView(LoginRequiredMixin, TemplateResponseMixin, View):
    template_name = 'registrations/registration_start.html'

    def get(self, request, eventid):
        event = get_object_or_404(Event.objects.for_user(request.user), pk=eventid)
        try:
            registration = Registration.objects.get(
                event=event,
                user=request.user,
                is_current=True,
            )
            if registration.status.PREPARATION_IN_PROGRESS:
                return redirect('registrations:step_registration_options', registration.id)
            else:
                return redirect('registrations:step_final_check', registration.id)
        except Registration.DoesNotExist:
            return self.render_to_response({
                'event': event,
            })

    def post(self, request, eventid):
        event = get_object_or_404(Event.objects.for_user(request.user), pk=eventid)
        with reversion.create_revision():
            reversion.set_user(self.request.user)
            reversion.set_comment(_("Registration started via frontend."))

            registration, created = Registration.objects.filter(is_current=True).get_or_create(
                event=event,
                user=request.user,
                defaults={'status': Registration.statuses.PREPARATION_IN_PROGRESS},
            )
        return redirect('registrations:step_registration_options', registration.id)


class RegistrationStepMixin(LoginRequiredMixin, ContextMixin):
    def get_queryset(self):
        # Only allow editing your own registrations
        return Registration.objects.filter(user=self.request.user)

    def get_success_url(self):
        # success_view is supplied by the subclass
        return reverse(self.success_view, args=(self.registration.id,))

    def setup(self, *args, **kwargs):
        super().setup(*args, **kwargs)

        self.registration = get_object_or_404(self.get_queryset(), pk=self.kwargs['pk'])

    @cached_property
    def event(self):
        return Event.objects.for_user(self.request.user).get(pk=self.registration.event_id)

    def dispatch(self, *args, **kwargs):
        if not self.registration.status.PREPARATION_IN_PROGRESS and not self.registration.status.PREPARATION_COMPLETE:
            # Let finalcheck sort out where to go
            return redirect('registrations:step_final_check', self.registration.id)

        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({
            'registration': self.registration,
            'event': self.event,
        })
        return super().get_context_data(**kwargs)


class RegistrationOptionsStep(RegistrationStepMixin, FormView):
    """ Step in registration process where user chooses options """

    template_name = 'registrations/step_registration_options.html'
    success_view = 'registrations:step_personal_details'
    form_class = RegistrationOptionsForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'event': self.event,
            'user': self.request.user,
            'registration': self.registration,
        })
        return kwargs

    def form_valid(self, form):
        if form.has_changed():
            with reversion.create_revision():
                form.save(self.registration)
                reversion.set_user(self.request.user)
                reversion.set_comment(_("Options updated via frontend. The following "
                                      "fields changed: %(fields)s" % {'fields': ", ".join(form.changed_data)}))

        return super().form_valid(form)

    def dispatch(self, *args, **kwargs):
        # No fields? Just skip this step
        if not self.event.registration_fields.all():
            return redirect(self.get_success_url())
        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        kwargs.update({
            'cancel_url': reverse('core:dashboard'),
        })
        return super().get_context_data(**kwargs)


class PersonalDetailsStep(RegistrationStepMixin, FormView):
    """ Step in registration process where user fills in personal details """

    template_name = 'registrations/step_personal_details.html'
    success_view = 'registrations:step_medical_details'
    form_class = PersonalDetailForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            address = self.request.user.address
        except ArtaUser.address.RelatedObjectDoesNotExist:
            address = Address(user=self.request.user)

        kwargs.update({
            'user': self.request.user,
            'address': address,
        })
        return kwargs

    def form_valid(self, form):
        if form.has_changed():
            with reversion.create_revision():
                form.save()
                reversion.set_user(self.request.user)
                fields = form.user_form.changed_data + form.address_form.changed_data
                reversion.set_comment(_("Personal info updated via frontend. The following "
                                        "fields changed: %(fields)s" % {'fields': ", ".join(fields)}))

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({
            'back_url': reverse('registrations:step_registration_options', args=(self.registration.pk,)),
        })
        return super().get_context_data(**kwargs)


class MedicalDetailsStep(RegistrationStepMixin, FormView):
    """ Step in registration process where user fills in medical details """

    template_name = 'registrations/step_medical_details.html'
    success_view = 'registrations:step_emergency_contacts'
    form_class = MedicalDetailForm

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        try:
            details = self.request.user.medical_details
        except ArtaUser.medical_details.RelatedObjectDoesNotExist:
            details = MedicalDetails(user=self.request.user)

        kwargs.update({
            'instance': details,
        })
        return kwargs

    def form_valid(self, form):
        if form.has_changed():
            with reversion.create_revision():
                # Make sure a revision is generated even when MedicalDetails is deleted
                # TODO: This is a workaround, see https://github.com/etianen/django-reversion/issues/830
                reversion.add_to_revision(form.instance)
                form.save(registration=self.registration)
                reversion.set_user(self.request.user)
                reversion.set_comment(_("Medical info updated via frontend. The following "
                                      "fields changed: %(fields)s" % {'fields': ", ".join(form.changed_data)}))

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({
            'back_url': reverse('registrations:step_personal_details', args=(self.registration.pk,)),
        })
        return super().get_context_data(**kwargs)


class EmergencyContactsStep(RegistrationStepMixin, FormView):
    """ Step in registration process where user fills in emergency contacts """

    template_name = 'registrations/step_emergency_contacts.html'
    success_view = 'registrations:step_final_check'
    form_class = EmergencyContactFormSet

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()

        kwargs.update({
            'instance': self.request.user,
        })
        return kwargs

    def form_valid(self, form):
        if form.has_changed():
            with reversion.create_revision():
                form.save()
                reversion.set_user(self.request.user)
                reversion.set_comment(_("Emergency contacts updated via frontend."))

        try:
            with reversion.create_revision():
                RegistrationStatusService.preparation_completed(self.registration)
                reversion.set_user(self.request.user)
                reversion.set_comment(_("Registration preparation completed via frontend."))
        except ValidationError as ex:
            messages.error(self.request, ex)
            return self.form_invalid(form)

        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        kwargs.update({
            # Broken?
            'back_url': reverse('registrations:step_medical_details', args=(self.registration.pk,)),
        })
        res = super().get_context_data(**kwargs)
        # FormView does not know we're using a formset, but it makes the template more readable like this
        res['formset'] = res['form']
        return res


class FinalCheck(RegistrationStepMixin, FormView):
    """ Step in registration process where user checks all information and agrees to conditions """

    template_name = 'registrations/step_final_check.html'
    success_view = 'registrations:registration_confirmation'
    form_class = FinalCheckForm

    def get_modify_url(self):
        return reverse('registrations:step_registration_options', args=(self.registration.pk,))

    def form_valid(self, form):
        try:
            # This intentionally does *not* create a revision for performance reasons (to make the registration request
            # as a whole, but also the transaction that has the event locked, shorter).
            RegistrationStatusService.finalize_registration(self.registration)
        except ValidationError as ex:
            messages.error(self.request, ex)

            return self.form_invalid(form)

        # Confirm registration by e-mail
        RegistrationNotifyService.send_confirmation_email(self.request, self.registration)

        return super().form_valid(form)

    def dispatch(self, *args, **kwargs):
        if self.registration.status.ACTIVE:
            return redirect(self.get_success_url())
        elif self.registration.status.PREPARATION_IN_PROGRESS:
            return redirect(self.get_modify_url())
        elif not self.registration.status.PREPARATION_COMPLETE:
            raise Http404("Registration in invalid state")

        return super().dispatch(*args, **kwargs)

    def get_context_data(self, **kwargs):
        personal_details = Address.objects.filter(user=self.request.user).first()
        medical_details = MedicalDetails.objects.filter(user=self.request.user).first()
        emergency_contacts = self.request.user.emergency_contacts.all()

        options = self.registration.options.all().select_related('option', 'field')
        any_is_full = self.event.full or any(value.option.full for value in options)
        total_price = sum(o.price for o in options if o.price is not None)

        kwargs.update({
            'user': self.request.user,
            'registration': self.registration,
            'event': self.event,
            'pdetails': personal_details,
            'mdetails': medical_details,
            'emergency_contacts': emergency_contacts,
            'any_is_full': any_is_full,
            'options': options,
            'total_price': total_price,
            'modify_url': self.get_modify_url(),
        })
        return super().get_context_data(**kwargs)


class RegistrationConfirmationView(LoginRequiredMixin, DetailView):
    """ View confirmation after registration. """

    context_object_name = 'registration'
    template_name = 'registrations/registration_confirmation.html'

    def get_queryset(self):
        return Registration.objects.filter(user=self.request.user)

    def get(self, *args, **kwargs):
        obj = self.get_object()
        if not obj.status.ACTIVE:
            return redirect('core:dashboard')
        return super().get(*args, **kwargs)
