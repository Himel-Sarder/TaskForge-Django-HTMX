from django.contrib.auth.models import User
from django.core.checks import messages
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST, require_http_methods
from django.utils import timezone
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from .models import Board, List, Task
from .forms import TaskForm, ListForm
import json
from django.db.models import Q
from datetime import datetime
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.shortcuts import redirect
from django.core.exceptions import PermissionDenied

def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('home')
    else:
        form = UserCreationForm()
    return render(request, 'registration/signup.html', {'form': form})

def user_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('home')
    else:
        form = AuthenticationForm()
    return render(request, 'registration/login.html', {'form': form})

def user_logout(request):
    logout(request)
    return redirect('login')

@login_required
def home(request):
    board = Board.objects.filter(
        Q(owner=request.user) | Q(members=request.user)
    ).prefetch_related('lists__tasks').first()

    if not board:
        return render(request, 'boards/no_boards.html')

    if request.headers.get('HX-Request'):
        if 'create-board' in request.GET:
            return render(request, 'boards/partials/create_board_form.html')

    filter_type = request.GET.get('filter', 'all')
    search_query = request.GET.get('search', '')

    if request.headers.get('HX-Request'):
        lists = []
        for list_obj in board.lists.all():
            tasks = list_obj.tasks.all()

            # Apply filters
            if filter_type == 'active':
                tasks = tasks.filter(is_completed=False)
            elif filter_type == 'completed':
                tasks = tasks.filter(is_completed=True)
            elif filter_type == 'overdue':
                tasks = tasks.filter(
                    is_completed=False,
                    due_date__lt=timezone.now().date()
                )

            # Apply search
            if search_query:
                try:
                    # Try to parse as date
                    search_date = datetime.strptime(search_query, '%Y-%m-%d').date()
                    tasks = tasks.filter(
                        Q(title__icontains=search_query) |
                        Q(due_date=search_date)
                    )
                except ValueError:
                    # If not a date, search only title
                    tasks = tasks.filter(title__icontains=search_query)

            list_obj.filtered_tasks = tasks.order_by('order')
            lists.append(list_obj)

        return render(request, 'boards/partials/filtered_list.html', {
            'lists': lists,
            'filter_type': filter_type,
            'search_query': search_query
        })

    return render(request, 'boards/home.html', {
        'board': board,
        'filter_type': filter_type,
        'search_query': search_query
    })

@require_http_methods(["POST"])
def add_list(request):
    board = Board.objects.filter(Q(owner=request.user) | Q(members=request.user)).first()

    form = ListForm(request.POST)

    if form.is_valid():
        list_obj = form.save(commit=False)
        list_obj.board = board
        list_obj.order = board.lists.count()
        list_obj.save()
        return redirect('home')

    return render(request, 'boards/home.html', {
        'board': board,
        'list_form': form
    })


@login_required
def add_task(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)
    if not list_obj.board.has_access(request.user):
        raise PermissionDenied

    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.list = list_obj
            task.order = list_obj.tasks.count()
            task.created_by = request.user
            task.save()
            return render(request, 'boards/partials/task_card.html', {'task': task})
        return render(request, 'boards/partials/task_form.html', {
            'form': form,
            'list_id': list_id
        }, status=400)

    # GET request - return empty form
    return render(request, 'boards/partials/task_form.html', {
        'form': TaskForm(),
        'list_id': list_id
    })


@require_http_methods(["DELETE"])
def delete_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    list_obj = task.list
    task.delete()

    tasks = list_obj.tasks.order_by('order')
    return render(request, 'boards/partials/task_list.html', {
        'tasks': tasks,
        'list_id': list_obj.id
    })


@require_http_methods(["GET", "POST"])
def edit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)

    if request.method == "POST":
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            task = form.save()
            return render(request, 'boards/partials/task_card.html', {'task': task})
    else:
        form = TaskForm(instance=task)

    return render(request, 'boards/partials/task_edit.html', {
        'form': form,
        'task': task
    })


@require_POST
def toggle_task(request, task_id):
    task = get_object_or_404(Task, id=task_id)
    task.is_completed = not task.is_completed
    task.completed_at = timezone.now() if task.is_completed else None
    task.save()
    return render(request, 'boards/partials/task_card.html', {'task': task})


@csrf_exempt
@require_POST
def reorder_tasks(request, list_id):
    try:
        data = json.loads(request.body)
        task_ids = data.get('task_ids', [])

        with transaction.atomic():
            for index, task_id in enumerate(task_ids):
                Task.objects.filter(id=task_id, list_id=list_id).update(order=index)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)


@csrf_exempt
@require_POST
def reorder_lists(request):
    try:
        data = json.loads(request.body)
        list_ids = data.get('list_ids', [])

        with transaction.atomic():
            for index, list_id in enumerate(list_ids):
                List.objects.filter(id=list_id).update(order=index)

        return JsonResponse({'status': 'success'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)}, status=400)

@login_required
def share_board(request, board_id):
    board = get_object_or_404(Board, id=board_id, owner=request.user)
    if request.method == 'POST':
        username = request.POST.get('username')
        try:
            user = User.objects.get(username=username)
            board.members.add(user)
            return redirect('board_settings', board_id=board.id)
        except User.DoesNotExist:
            messages.error(request, "User not found")
    return render(request, 'boards/share.html', {'board': board})


from django.views.decorators.csrf import ensure_csrf_cookie

@ensure_csrf_cookie
@login_required
def create_board(request):
    if request.method == 'POST':
        board = Board.objects.create(
            name=request.POST.get('name', 'New Board'),
            owner=request.user
        )
        if request.headers.get('HX-Request'):
            return redirect('home')
        return redirect('home')
    return render(request, 'boards/partials/create_board_form.html')


@login_required
@login_required
def create_list(request):
    if request.method == 'POST':
        # Get the most recent board owned by the user
        board = Board.objects.filter(owner=request.user).first()

        if not board:
            return JsonResponse({'error': 'No board exists'}, status=400)

        list_name = request.POST.get('name', 'New List')
        new_list = List.objects.create(
            name=list_name,
            board=board,
            order=board.lists.count()
        )

        if request.headers.get('HX-Request'):
            return render(request, 'boards/partials/list_column.html', {'list': new_list})
        return redirect('home')

    # GET request - return just the form
    return render(request, 'boards/partials/create_list_form.html')


@require_http_methods(["DELETE"])
@login_required
def delete_list(request, list_id):
    list_obj = get_object_or_404(List, id=list_id)

    if not list_obj.board.has_access(request.user):
        raise PermissionDenied

    list_obj.delete()  # This also deletes tasks if on_delete=models.CASCADE
    return HttpResponse('')

