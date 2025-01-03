from django.shortcuts import render, redirect
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login, logout
from django.views import View
from django.db import transaction
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from .models import Task
from .forms import PositionForm
import pytz
from django.utils import timezone
from twilio.rest import Client
from twilio.base.exceptions import TwilioRestException

@csrf_exempt
def logout_view(request):
    logout(request)
    return redirect('login')

@method_decorator(csrf_exempt, name='dispatch')
class CustomLoginView(LoginView):
    template_name = 'base/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('tasks')

@method_decorator(csrf_exempt, name='dispatch')
class RegisterPage(FormView):
    template_name = 'base/register.html'
    form_class = UserCreationForm
    redirect_authenticated_user = True
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        user = form.save()
        if user is not None:
            login(self.request, user)
            print(f"User {user.username} registered and logged in successfully.")
        return super(RegisterPage, self).form_valid(form)

    def form_invalid(self, form):
        print("Registration failed. Errors:")
        for field, errors in form.errors.items():
            print(f"{field}: {', '.join(errors)}")
        return super(RegisterPage, self).form_invalid(form)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('tasks')
        return super(RegisterPage, self).get(*args, **kwargs)

@method_decorator(csrf_exempt, name='dispatch')
class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'tasks'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = context['tasks'].filter(user=self.request.user)
        context['count'] = context['tasks'].filter(complete=False).count()

        search_input = self.request.GET.get('search-area') or ''
        if search_input:
            context['tasks'] = context['tasks'].filter(title__contains=search_input)

        context['search_input'] = search_input
        return context

@method_decorator(csrf_exempt, name='dispatch')
class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'base/task.html'

@method_decorator(csrf_exempt, name='dispatch')
class TaskCreate(LoginRequiredMixin, CreateView):
    model = Task
    fields = ['title', 'description', 'complete']
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        form.instance.user = self.request.user
        print(f"Task Created: Title - {form.instance.title}, Description - {form.instance.description}, Complete - {form.instance.complete}")

        account_sid = 'AC9aa339278939d26296616d2ff2fba460'
        auth_token = 'b40d4854074d3c82cecee1df37605f2a'
        client = Client(account_sid, auth_token)

        try:
            title = form.instance.title.upper()
            title = "*" + title + "*"

            message = client.messages.create(
                from_='whatsapp:+14155238886',
                body=f'''{title}
                
                Contents :{form.instance.description}''',
                to='whatsapp:+918919426801'
            )
            print("Message sent successfully:", message.sid)
        except TwilioRestException as e:
            print(f"Twilio Error: {e}")
            print(f"Error Code: {e.code}, Message: {e.msg}")
        except Exception as e:
            print(f"Unexpected Error: {e}")

        return super(TaskCreate, self).form_valid(form)

@method_decorator(csrf_exempt, name='dispatch')
class TaskUpdate(LoginRequiredMixin, UpdateView):
    model = Task
    fields = ['title', 'description', 'complete']
    success_url = reverse_lazy('tasks')

@method_decorator(csrf_exempt, name='dispatch')
class DeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    success_url = reverse_lazy('tasks')

    def get_queryset(self):
        owner = self.request.user
        return self.model.objects.filter(user=owner)

@method_decorator(csrf_exempt, name='dispatch')
class TaskReorder(View):
    def post(self, request):
        form = PositionForm(request.POST)
        if form.is_valid():
            positionList = form.cleaned_data["position"].split(',')
            with transaction.atomic():
                self.request.user.set_task_order(positionList)
        return redirect(reverse_lazy('tasks'))

@csrf_exempt
def send_uncompleted_tasks(request):
    india_tz = pytz.timezone("Asia/Calcutta")
    current_time = timezone.localtime(timezone.now()).astimezone(india_tz)

    uncompleted_tasks = Task.objects.filter(complete=False)
    task_titles = "*\n\n*".join([task.title for task in uncompleted_tasks]).upper()

    account_sid = 'AC9aa339278939d26296616d2ff2fba460'
    auth_token = 'b40d4854074d3c82cecee1df37605f2a'
    client = Client(account_sid, auth_token)

    try:
        message = client.messages.create(
            from_='whatsapp:+14155238886',
            body=f'''*{task_titles}*''',
            to='whatsapp:+918919426801'
        )
        print("Message sent successfully:", message.sid)
    except TwilioRestException as e:
        print(f"Twilio Error: {e}")
        print(f"Error Code: {e.code}, Message: {e.msg}")
    except Exception as e:
        print(f"Unexpected Error: {e}")

    return redirect('tasks')

@csrf_exempt
def delete_all(request):
    Task.objects.all().delete()
    return redirect('tasks')
