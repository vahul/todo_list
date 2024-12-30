from django.shortcuts import render, redirect,HttpResponse
from django.views.generic.list import ListView
from django.views.generic.detail import DetailView
from django.views.generic.edit import CreateView, UpdateView, DeleteView, FormView
from django.urls import reverse_lazy
import pytz

from datetime import timezone
from django.contrib.auth.views import LoginView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

from django.contrib.auth import logout

# Imports for Reordering Feature
from django.views import View
from django.shortcuts import redirect
from django.db import transaction

from .models import Task
from .forms import PositionForm
def logout_view(request):
    logout(request)
    return redirect('login')
class CustomLoginView(LoginView):
    template_name = 'base/login.html'
    fields = '__all__'
    redirect_authenticated_user = True

    def get_success_url(self):
        return reverse_lazy('tasks')


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
        else:
            print("User registration failed.")
        return super(RegisterPage, self).form_valid(form)

    def get(self, *args, **kwargs):
        if self.request.user.is_authenticated:
            return redirect('tasks')
        return super(RegisterPage, self).get(*args, **kwargs)


class TaskList(LoginRequiredMixin, ListView):
    model = Task
    context_object_name = 'tasks'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['tasks'] = context['tasks'].filter(user=self.request.user)
        context['count'] = context['tasks'].filter(complete=False).count()

        search_input = self.request.GET.get('search-area') or ''
        if search_input:
            context['tasks'] = context['tasks'].filter(
                title__contains=search_input)

        context['search_input'] = search_input

        return context


class TaskDetail(LoginRequiredMixin, DetailView):
    model = Task
    context_object_name = 'task'
    template_name = 'base/task.html'


class TaskCreate(LoginRequiredMixin, CreateView):
    model = Task
    fields = ['title', 'description', 'complete']
    success_url = reverse_lazy('tasks')

    def form_valid(self, form):
        form.instance.user = self.request.user
        print(f"Task Created: Title - {form.instance.title}, Description - {form.instance.description}, Complete - {form.instance.complete}")
        from twilio.rest import Client

        account_sid = 'AC9aa339278939d26296616d2ff2fba460'
        auth_token = 'b40d4854074d3c82cecee1df37605f2a'
        client = Client(account_sid, auth_token)

        # message = client.messages.create(
        #   from_='whatsapp:+14155238886',
        #   content_sid='HXb5b62575e6e4ff6129ad7c8efe1f983e',
        #   content_variables='{"1":"12/1","2":"3pm"}',
        #   to='whatsapp:+918919426801'
        # )
        title=form.instance.title
        title=title.upper()
        title="*"+title+"*"
        message2 = client.messages.create(
            from_='whatsapp:+14155238886',
            body=f'''{title}
            
            Contents :{form.instance.description}''',
            to='whatsapp:+918919426801'
        )
        return super(TaskCreate, self).form_valid(form)


class TaskUpdate(LoginRequiredMixin, UpdateView):
    model = Task
    fields = ['title', 'description', 'complete']
    success_url = reverse_lazy('tasks')


class DeleteView(LoginRequiredMixin, DeleteView):
    model = Task
    context_object_name = 'task'
    success_url = reverse_lazy('tasks')
    def get_queryset(self):
        owner = self.request.user
        return self.model.objects.filter(user=owner)

class TaskReorder(View):
    def post(self, request):
        form = PositionForm(request.POST)

        if form.is_valid():
            positionList = form.cleaned_data["position"].split(',')

            with transaction.atomic():
                self.request.user.set_task_order(positionList)

        return redirect(reverse_lazy('tasks'))

from django.test import TestCase
from django.utils import timezone
import pytz
from twilio.rest import Client
import os

def send_uncompleted_tasks(request):
    # Get current time in India timezone
    india_tz = pytz.timezone("Asia/Calcutta")
    current_time = timezone.localtime(timezone.now()).astimezone(india_tz)  # Ensure time is in local timezone

    # Filter uncompleted tasks
    uncompleted_tasks = Task.objects.filter(complete=False)
    print(uncompleted_tasks)

    # Create the message
    task_titles = "*\n\n*".join([task.title for task in uncompleted_tasks])
    task_titles=task_titles.upper()
    # Send the message using Twilio
    account_sid = 'AC9aa339278939d26296616d2ff2fba460'
    auth_token = 'b40d4854074d3c82cecee1df37605f2a'
    client = Client(account_sid, auth_token)
    message = client.messages.create(
        from_='whatsapp:+14155238886',
        body=f'''*{task_titles}*''',
        to='whatsapp:+918919426801'
    )
    return redirect('tasks')


def delete_all(request):
    Task.objects.all().delete()
    return redirect('tasks')