from django.shortcuts import render
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from .models import Category, Page
from .forms import CategoryForm, PageForm, UserForm, UserProfileForm
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from datetime import datetime

# Create your views here.
def index(request):
    request.session.set_test_cookie()
    # Query the database for a list of All categories currently stored
    # Order the categories by no. of likes in descending order
    # Retrieve the top 5 only - or all if less than 5
    # Place the list in out context_dict dictionary
    # that will be passed to the template engine

    category_list = Category.objects.order_by('-likes')[:5]

    # Querying for most liked 5 pages
    pages_list = Page.objects.order_by('-views')[:5]
    context_dict = {'categories':category_list,
                    'pages':pages_list}
    
    # Call function to handle the cookies
    visitor_cookie_handler(request,)
    context_dict['visits'] = request.session['visits']

    response = render(request, 'rango/index.html', context_dict)

    # Render the response back to the user, updating any cookies that need changed
    return response

def views(request):
    return HttpResponse("Hello views")

def about(request):
    if request.session.test_cookie_worked():	
        print('TEST COOKIE WORKED')	
        request.session.delete_test_cookie()
    return render(request, 'rango/about.html',{})

def show_category(request, category_name_url):
    # Create a context dictionary which we can pass
    # to  the template rendering engine
    context_dict = {}
    try:
        # Can we find a category name slug with the given name?
        # If we can't, find the .get() method raises a DoesnNotExist exception.
        # So the .get() method returns one modesl instance or raise an exception
        category = Category.objects.get(slug=category_name_url)

        # Retrieve all of the associated pages.
        # Note that filter() will return a list of page objects or an empty list
        pages = Page.objects.filter(category=category)

        # Adds our results list to the template context under name pages.
        context_dict['pages'] = pages
        # We also add the category object from
        # the database to the context dictionary.
        # We'll use this in the template to verify that the category exists.
        context_dict['category']=category
    except Category.DoesNotExist:
            # We get here if we didn't find the specified category.
            # Don't do anything -
            # the template will display the "no category" message for us.
            context_dict['category'] = None
            context_dict['pages']=None
    return render(request, 'rango/category.html', context_dict)

def add_category(request):
    form=CategoryForm()

    # A HTTP POST?
    if request.method == 'POST':
        form = CategoryForm(request.POST)

        # Have we been provided with a valid form?
        if form.is_valid():
            # Save the new category to the database.
            form.save(commit=True)
            # Now that the category is saved
            # We could give a confirmation message
            # But since the most recent category added is on the index page
            # Then we can direct the user block to the index page.
            return index(request)
        else:
            # The supplied form contained errors -
            # just print them to the terminal.
            print(form.errors)
    # Will handle the bad form, new form, or no form supplied cases.
    # Render the form with error mesages (if any).
    return render(request, 'rango/add_category.html',{'form':form})

def add_page(request, category_name_url):
    try:
        category = Category.objects.get(slug=category_name_url)
    except Category.DoesNotExist:
        category = None

    form = PageForm()
    if request.method == 'POST':
        form = PageForm(request.POST)
        if form.is_valid():
            if category:
                page = form.save(commit=False)
                page.category = category
                page.views = 0
                page.save()
                return show_category(request, category_name_url)
        else:
            print (form.errors)
    context_dict = {'form':form, 'category':category}
    return render(request, 'rango/add_page.html', context_dict)

def register(request):
    # A boolean value for telling the template 
    # whether the registration was successful.
    # Set to False initially, Code changes value to 
    # True when registration succeeds.
    registered = False

    # If it's a HTTP POST, we're interested in processing form data.
    if request.method == 'POST':
        # Attempt to grab information from the raw form information.
        # Note that we make use of both UserForm and UserProfileForm.
        user_form = UserForm(data=request.POST)
        profile_form = UserProfileForm(data=request.POST)

        # If the two forms are valid....
        if user_form.is_valid() and profile_form.is_valid():
            # Save the user's form data to the database.
            user = user_form.save()

            # Now we hash the password with the set_password method.
            # Once, hashed, we can update the user object.
            user.set_password(user.password)
            user.save()

            # Now sort out the UserProfile instance.
            # Since we need to set the user attribute ourselves.
            # we set commit=False. This delays saving the model
            # until we're ready to avoid integrity problems.
            profile = profile_form.save(commit=False)
            profile.user = user

            # Did the user provide a profile picture?
            # If so, we need to get it from the input form and 
            # put it in the UserProfile model.
            if 'picture' in request.FILES:
                profile.picture = request.FILES['picture']

            # Now we save the UserProfile model instance.
            profile.save()

            # update our varibale to indicate that the template
            # registration was successful.
            registered = True
        else:
            # Invalid form or forms - mistakes or something else?
            # Print problems to the terminal.
            print(user_form.errors, profile_form.errors)
    else:
        # Not a HTTP POST, so we render our form using two MOdelForm instances.
        # These forms will be blank, ready for user input
        user_form = UserForm()
        profile_form = UserProfileForm()
    
    # Render the template depending on the context
    return render(request, 
                  'rango/register.html',
                  {'user_form': user_form,
                   'profile_form': profile_form,
                   'registered':registered})

def user_login(request):
    # If the request is a HTTP POST, try to pull out the relevant information.
    if request.method == 'POST':
        # Gather the username and password provided by the user.
        # This information is obtained from the login form.
        # We use request.POST.get('<variable>') as opposed
        # to request.POST.get['<variable>'], because the
        # request.POST.get('<variable>') returns None if the 
        # value does not exist, while request.POST['<variable>']
        # will raise a KeyError exception.
        username = request.POST.get('username')
        password = request.POST.get('password')

        # Use Django's machinery to attempt to see if the username/password
        # combination is valid - a User object is returned if it is.
        user = authenticate(username=username, password=password)

        # If we have a User object, the details are correct.
        # If None(Python's way of representing the absense of value)
        # with macthing credentials was found
        if user:
            # Is the account active? It could have been disabled
            if user.is_active:
                # If the account is valid and avtive, we can log the user in.
                # we'll send the user back to the homepage.
                login(request, user)
                return HttpResponseRedirect(reverse('rango:index'))
            else:
                # An inactive account was used - no logging in!
                return HttpResponse("Your Rango account is disabled.")
        else:
            # Bad login details were provided. So we can't login the user in.
            return HttpResponse("Your Rango account is disabled")
    
    # The request is not a HTTP pOST, so display the login form.
    # This scenario would most likely be a HTTP GET.
    else:
        # No context variable to pass to the template system, hence the
        # blank dictionary object....
        return render(request, 'rango/login.html', {})

@login_required
def restricted(request):
    return HttpResponse("Since you're logged in, you can see this text")

@login_required
def user_logout(request):
    # Since we know the user is logged in, we can now just log them out.
    logout(request)
    # Take the user back to the homepage.
    return HttpResponseRedirect(reverse('rango:index'))

# A helper method
def get_server_side_cookie(request, cookie, default_val=None):
    """
    storing session data server-side
    only works however for built-in types, such as int, float, long, complex and boolean
    """
    val = request.session.get(cookie)
    if not val:
        val = default_val
    return val

# Updated the function definition
def visitor_cookie_handler(request):
    visits = int(get_server_side_cookie(request, 'visits', 1))
    last_visit_cookie = get_server_side_cookie(request,
                                                'last_visit',
                                                str(datetime.now()))
    last_visit_time = datetime.strptime(last_visit_cookie[:-7],
                                        '%Y-%m-%d %H:%M:%S')

    # If it's been more than a day since the last visit.....
    if (datetime.now()-last_visit_time).days >0:
        visits = visits + 1
        # Update the last visit cookie now that we have updated the couunt
        request.session['last_visit'] = str(datetime.now())
    else:
        visits = 1
        # Set the last visit cookie now that we have updated the count
        request.session['last_visit'] = last_visit_cookie
    
    # Update/set the visits cookie
    request.session['visits'] = visits