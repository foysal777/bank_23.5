from django.core.mail import EmailMessage,EmailMultiAlternatives
from django.template.loader import render_to_string
from django.contrib import messages
from account_app.models import UserAccount
from transaction.models import BankStatus
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.utils import timezone
from django.shortcuts import get_object_or_404, redirect,render
from django.views import View
from django.http import HttpResponse
from django.views.generic import CreateView, ListView
# from transactions.constants import DEPOSIT, WITHDRAWAL,LOAN, LOAN_PAID
from datetime import datetime
from django.db.models import Sum
from transaction.forms import (
    DepositForm,
    WithdrawForm,
    LoanRequestForm,
    TransferForm
)
from transaction.models import Transaction
DEPOSIT = 1
WITHDRAWAL = 2
LOAN = 3
LOAN_PAID = 4

TRANSACTION_TYPE = (
    (DEPOSIT, 'Deposite'),
    (WITHDRAWAL, 'Withdrawal'),
    (LOAN, 'Loan'),
    (LOAN_PAID, 'Loan Paid'),
    
)


def send_transaction_email(user, amount, subject, template_name):
        message = render_to_string(template_name, {
            'user' : user,
            'amount' : amount,
        })
        send_email = EmailMultiAlternatives(subject, '', to=[user.email])
        send_email.attach_alternative(message, "text/html")
        send_email.send()

 

# use mixin for the inherite multiple pages 
class TransactionCreateMixin(LoginRequiredMixin, CreateView):
    template_name = 'transaction_form.html'
    model = Transaction
    title = ''
    success_url = reverse_lazy('transaction_report')
# inherite html code 

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({
            'account': self.request.user.account
        })
        return kwargs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs) # template e context data pass kora
        context.update({
            'title': self.title
        })

        return context


class DepositMoneyView(TransactionCreateMixin):
    form_class = DepositForm
    title = 'Deposit'

    def get_initial(self):
        initial = {'transaction_type': DEPOSIT}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        account = self.request.user.account
        # if not account.initial_deposit_date:
        #     now = timezone.now()
        #     account.initial_deposit_date = now
        account.balance += amount # amount = 200, tar ager balance = 0 taka new balance = 0+200 = 200
        account.save(
            update_fields=[
                'balance'
            ]
        )

        messages.success(
            self.request,
            f'{"{:,.2f}".format(float(amount))}$ was deposited to your account successfully'
        )
        
        send_transaction_email(self.request.user, amount, "Deposite Message", "deposite_email.html")
        
        
        return super().form_valid(form)
        
       


class WithdrawMoneyView(TransactionCreateMixin):
    form_class = WithdrawForm
    title = 'Withdraw Money'

    def get_initial(self):
        initial = {'transaction_type': WITHDRAWAL}
        return initial

    def form_valid(self, form):
        bank_status = BankStatus.objects.first()
        if bank_status and bank_status.is_bankrupt:
            messages.error(self.request, 'The bank is bankrupt. Unable to withdraw any amount.')
            return redirect(reverse_lazy('home'))  

        amount = form.cleaned_data.get('amount')
        user_account = self.request.user.account
        if amount > user_account.balance:
            messages.error(self.request, 'Insufficient funds in your account.')
            return redirect(reverse_lazy('home')) 
        user_account.balance -= amount
        user_account.save(update_fields=['balance'])

        messages.success(
            self.request,
            f'Successfully withdrawn {"{:,.2f}".format(float(amount))}$ from your account'
        )

        send_transaction_email(self.request.user, amount, "withdraw Message", "withdraw_email.html")

        return super().form_valid(form)





class LoanRequestView(TransactionCreateMixin):
    form_class = LoanRequestForm
    title = 'Request For Loan'

    def get_initial(self):
        initial = {'transaction_type': LOAN}
        return initial

    def form_valid(self, form):
        amount = form.cleaned_data.get('amount')
        current_loan_count = Transaction.objects.filter(
            account=self.request.user.account,transaction_type=3,loan_approve=True).count()
        if current_loan_count >= 3:
            return HttpResponse("You have cross the loan limits")
        messages.success(
            self.request,
            f'Loan request for {"{:,.2f}".format(float(amount))}$ submitted successfully'
        )


        send_transaction_email(self.request.user, amount, "Loan Request Message", "loan_email.html")

        return super().form_valid(form)
    
class TransactionReportView(LoginRequiredMixin, ListView):
    template_name = 'transaction_report.html'
    model = Transaction
    balance = 0 # filter korar pore ba age amar total balance ke show korbe
    
    def get_queryset(self):
        queryset = super().get_queryset().filter(
            account=self.request.user.account
        )
        start_date_str = self.request.GET.get('start_date')
        end_date_str = self.request.GET.get('end_date')
        
        if start_date_str and end_date_str:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
            
            queryset = queryset.filter(timestamp__date__gte=start_date, timestamp__date__lte=end_date)
            self.balance = Transaction.objects.filter(
                timestamp__date__gte=start_date, timestamp__date__lte=end_date
            ).aggregate(Sum('amount'))['amount__sum']
        else:
            self.balance = self.request.user.account.balance
       
        return queryset.distinct() # unique queryset hote hobe
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'account': self.request.user.account
        })

        return context
    
        
class PayLoanView(LoginRequiredMixin, View):
    def get(self, request, loan_id):
        loan = get_object_or_404(Transaction, id=loan_id)
        print(loan)
        if loan.loan_approve:
            user_account = loan.account
              
            if loan.amount < user_account.balance:
                user_account.balance -= loan.amount
                loan.balance_after_transaction = user_account.balance
                user_account.save()
                loan.loan_approved = True
                loan.transaction_type = LOAN_PAID
                loan.save()
                return redirect('transactions:loan_list')
            else:
                messages.error(
            self.request,
            f'Loan amount is greater than available balance'
        )

        return redirect('loan_list')


class LoanListView(LoginRequiredMixin,ListView):
    model = Transaction
    template_name = 'loan_request.html'
    context_object_name = 'loans' # loan list ta ei loans context er moddhe thakbe
    
    def get_queryset(self):
        user_account = self.request.user.account
        queryset = Transaction.objects.filter(account=user_account,transaction_type=3)
        print(queryset)
        return queryset
    
    

# send money one account to another account 

class TransferView(LoginRequiredMixin, View):
    def get(self, request):
        form = TransferForm()
        return render(request, 'transfer.html', {'form': form})

    def post(self, request):
        user_account = request.user.account  
        form = TransferForm(request.POST, account=user_account)
        if form.is_valid():
            recipient = form.cleaned_data['recipient_account']
            amount = form.cleaned_data['amount']
            if user_account.balance >= amount:
                user_account.balance -= amount
                recipient.balance += amount
                user_account.save()
                recipient.save()
                send_transaction_email(self.request.user, amount, "Send Money Message", "transfer_email.html")
                messages.success(request, 'Transfer successfully completed')
            else:
                messages.error(request, 'Insufficient Balance in your account.')
        else:
            messages.error(request, 'Invalid input.')
        return render(request, 'transfer.html', {'form': form})