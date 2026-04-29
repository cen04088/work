from django.views.generic import TemplateView

class HomeView(TemplateView):
    template_name = 'core/home.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        from health.models import HealthClinic
        from jobs.models import EmploymentSupportCenter
        from pension.models import PensionSite

        context.update({
            "support_center_count": EmploymentSupportCenter.objects.count(),
            "clinic_count": HealthClinic.objects.count(),
            "pension_site_count": PensionSite.objects.count(),
        })
        return context

