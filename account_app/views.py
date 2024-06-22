from django.shortcuts import render,redirect
from django.views.generic import FormView,View
from .forms import RegistrationForm ,UserUpdateForm
from django.contrib.auth import login,logout
from django.urls import reverse_lazy
from transaction.views import send_transaction_email
from django.contrib.auth.views import LoginView,LogoutView
from django.contrib import messages
from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib.auth import authenticate, login , logout,update_session_auth_hash
from django.contrib.auth.forms import  AuthenticationForm,PasswordChangeForm,SetPasswordForm
# Create your views here.

def send_transaction_email( subject, template_name):
        message = render_to_string(template_name, {
        
          
        })
        send_email = EmailMultiAlternatives(subject, '')
        send_email.attach_alternative(message, "text/html")
        send_email.send()







class RegistrationView(FormView):
    template_name ='register.html'
    form_class = RegistrationForm
    success_url = reverse_lazy('register')
    
    def form_valid(self, form):
        user = form.save()
        login(self.request , user)
        print(user)
        messages.success( 'Register Completed')
        return super().form_valid(form)
    
    
class login_View(LoginView):
    template_name = 'log_in.html'
    def get_success_url(self):
        return reverse_lazy('home')
    

class log_outView(LogoutView):
   
    def get_success_url(self):
        if self.request.user.is_authenticated:
            logout(self.request)
            messages.success(
            self.request,
            f'Successfully Log out  your Account'
        )

        return reverse_lazy('home')    
    
class UserBankAccountUpdateView(View):
    template_name = 'profile.html'

    def get(self, request):
        form = UserUpdateForm(instance=request.user)
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = UserUpdateForm(request.POST, instance=request.user)
        if form.is_valid():
            form.save()
            return redirect('profile')  
        return render(request, self.template_name, {'form': form})
    
    
    
def pass_2(request):
    if  request.user.is_authenticated:
        if request.method == 'POST':
            pass_form = SetPasswordForm(request.user , data = request.POST )
           
            if pass_form.is_valid():                         
                pass_form.save()
                messages.success(request, 'Your Password is Already Changed Successfully')
                update_session_auth_hash(request, pass_form.user)                         
                return redirect('profile')
            
            
        else:
            pass_form = SetPasswordForm(request.user)
        
        send_transaction_email( " Message", "pass_email.html")


        return render(request, 'pass_cng.html', {'data' : pass_form})  
       
    else:
        return redirect('register')