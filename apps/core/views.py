
from django.shortcuts import render

# Create your views here.
def index(request):
    template_name='core/index.html'
    return render(request, template_name)


def about(request):
    template_name='core/about.html'
    return render(request, template_name)


def partnerwithus(request):
    template_name='core/partnerwithus.html'
    return render(request, template_name)


def contact(request):
    template_name='core/contact.html'
    return render(request, template_name)

def review(request):
    template_name='core/review.html'
    return render(request, template_name)