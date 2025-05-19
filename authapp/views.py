from django.shortcuts import render
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from db_connections import db
from django.contrib.auth.hashers import make_password, check_password
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.hashers import check_password
from db_connections import db

users = db["users"]

# --- Register Logic ---
def register_form(request):
    return render(request, "authapp/register.html")

class RegisterView(APIView):
    def post(self, request):
        data = request.POST
        if users.find_one({"email": data["email"]}):
            return render(request, "authapp/register.html", {"error": "Email already exists"})
        new_user = {
            "name": data["name"],
            "email": data["email"],
            "password": make_password(data["password"])
        }
        users.insert_one(new_user)
        return redirect("login_form")

# --- Login Logic ---

def login_form(request):
    if request.method == 'POST':
        print("Login POST received")  # DEBUG
        email = request.POST.get('email')
        password = request.POST.get('password')
        user = users.find_one({'email': email})

        if user and check_password(password, user['password']):
            print("Login success")  # DEBUG
            request.session['user_email'] = email
            print("REDIRECTING TO HOME")
            return redirect('home')
        else:
            print("Invalid login")  # DEBUG
            messages.error(request, "Invalid email or password.")
            return redirect('login_form')
    print("Login GET request")  # DEBUG
    return render(request, 'authapp/login.html')


# --- Home Page ---
def home_view(request):
    if not request.session.get("user_email"):
        return redirect("/login/")
    return render(request, "authapp/home.html")



# --- Upload API ---
class UploadFileView(APIView):
    def post(self, request):
        file = request.FILES.get("file")
        if file:
            save_path = f"media/uploads/{file.name}"
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            with open(save_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)
            return Response({"message": "File uploaded successfully"}, status=201)
        return Response({"error": "No file provided"}, status=400)

