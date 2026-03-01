from django.shortcuts import get_object_or_404, redirect
from django.views import View
from django.contrib import messages
from django.views.generic import ListView, TemplateView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Sum, Count, F, Q
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse
import csv

from .forms import CustomCreationForm, MaintenanceLogForm
from .models import Asset, MaintenanceLog
from .mixins import ManagerOrAdminRequiredMixin

# TOPIC 5: Class-Based Views (CBVs) & TOPIC 4: Aggregation
class DashboardView(LoginRequiredMixin, TemplateView):
    template_name = "assets/dashboard.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Aggregation: Calculate total value of all assets
        total_cost = Asset.objects.aggregate(total=Sum('cost'))['total'] or 0
        context['total_asset_value'] = total_cost

        # Annotation/Count: Assets per type
        context['assets_by_type'] = Asset.objects.values('asset_type').annotate(count=Count('id'))
        
        return context

# TOPIC 3: Optimize SQL Queries
class AssetListView(LoginRequiredMixin, ListView):
    model = Asset
    template_name = "assets/asset_list.html"
    context_object_name = "assets"
    paginate_by = 5

    def get_queryset(self):
        # Optimization: Use select_related to fetch the 'assigned_to' User 
        # in the same query, preventing the N+1 problem.
        queryset = Asset.objects.select_related('assigned_to').all()

        asset_type = self.request.GET.get('asset_type')
        search_query = self.request.GET.get('search')

        if asset_type:
            queryset = queryset.filter(asset_type=asset_type)

        if search_query:
            # Q objects allow us to search for the query in the asset name OR the assigned username
            queryset = queryset.filter(
                Q(name__icontains=search_query) | 
                Q(assigned_to__username__icontains=search_query)
            )
            
        return queryset
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['asset_types'] = Asset.ASSET_TYPES
        return context
    
class AssetCreateView(ManagerOrAdminRequiredMixin, CreateView):
    model = Asset
    template_name = "assets/asset_form.html"
    fields = ['name', 'asset_type', 'cost', 'assigned_to']
    success_url = reverse_lazy('asset-list')

    def form_valid(self, form):
        print(f"Creating asset: {form.instance.name}")
        return super().form_valid(form)

class AssetUpdateView(ManagerOrAdminRequiredMixin, UpdateView):
    model = Asset
    template_name = 'assets/asset_form.html'
    fields = ['name', 'asset_type', 'cost', 'assigned_to']
    success_url = reverse_lazy('asset-list')

class AssetDeleteView(ManagerOrAdminRequiredMixin, DeleteView):
    model = Asset
    template_name = 'assets/asset_confirm_delete.html'
    success_url = reverse_lazy('asset-list')

class AssetHistoryView(ManagerOrAdminRequiredMixin, ListView):
    template_name = "assets/asset_history.html"
    context_object_name = "history_records"

    def get_queryset(self):
        # Fetch the history specifically for this asset
        asset = get_object_or_404(Asset, pk=self.kwargs['pk'])
        return asset.history.all()

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['asset'] = get_object_or_404(Asset, pk=self.kwargs['pk'])
        return context

class AssetRevertView(ManagerOrAdminRequiredMixin, View):
    """Handles the rollback POST request."""
    def post(self, request, pk, history_id):
        asset = get_object_or_404(Asset, pk=pk)
        historical_record = get_object_or_404(asset.history.model, history_id=history_id)
        
        # Taking the historical state and saving it as the current active state
        historical_record.instance.save()
        
        messages.success(request, f"Asset successfully reverted to state from {historical_record.history_date}.")
        return redirect('asset-history', pk=pk)

class SignUpView(ManagerOrAdminRequiredMixin, CreateView):
    form_class = CustomCreationForm
    template_name = 'registration/register.html'
    success_url = reverse_lazy('dashboard')

class MaintenanceLogCreateView(LoginRequiredMixin, CreateView):
    model = MaintenanceLog
    form_class = MaintenanceLogForm
    template_name = 'assets/maintenancelog_form.html'
    success_url = reverse_lazy('asset-list')

    def form_valid(self, form):
        form.instance.asset = get_object_or_404(Asset, pk=self.kwargs['pk'])
        return super().form_valid(form)

def export_assets_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="asset_report.csv"'

    writer = csv.writer(response)
    writer.writerow(['Asset Name', 'Type', 'Cost', 'Assigned User'])

    assets = Asset.objects.select_related('assigned_to').all()
    for asset in assets:
        assigned_user = asset.assigned_to.username if asset.assigned_to else "Unassigned"
        writer.writerow([asset.name, asset.get_asset_type_display(), asset.cost, assigned_user])

    return response