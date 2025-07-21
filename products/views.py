from datetime import datetime, timedelta
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import Category, Product
from orders.models import Order, OrderItem
import matplotlib.pyplot as plt
import io
import base64
from accounts.decorators import merchant_required
from .forms import ProductForm


def home(request):
    categories = Category.objects.all()
    context = {
        'categories': categories,
    }
    return render(request, 'home.html', context)


def category_detail(request, pk):
    category = get_object_or_404(Category, pk=pk)
    products = Product.objects.filter(category=category)
    paginator = Paginator(products, 35)
    page = request.GET.get('page')
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    context = {
        'category': category,
        'products': products_page,
    }
    return render(request, 'products/category_detail.html', context)


def search_products(request):
    query = request.GET.get('q', '').strip()
    if query:
        products = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).distinct()
    else:
        products = Product.objects.all()
    paginator = Paginator(products, 35)
    page = request.GET.get('page')
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)
    context = {
        'category': None,
        'products': products_page,
        'search_query': query,
    }
    return render(request, 'products/category_detail.html', context)


@merchant_required
def merchant_dashboard(request):
    products = Product.objects.filter(merchant=request.user)
    return render(request, 'products/merchant_dashboard.html', {'products': products})


from django.shortcuts import render, redirect
from django.contrib import messages
from django.views import View
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.http import HttpResponseBadRequest
import logging

from .forms import ProductForm
from .models import Product

logger = logging.getLogger(__name__)


def merchant_required(view_func):
    """Decorator to ensure the user is a merchant."""

    @login_required
    def wrapper(request, *args, **kwargs):

        return view_func(request, *args, **kwargs)

    return wrapper


@method_decorator(merchant_required, name='dispatch')
class create_product(View):
    template_name = 'products/create_product.html'

    def get(self, request):
        form = ProductForm()
        return render(request, self.template_name, {'form': form})

    def post(self, request):
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                # Log incoming files for debugging
                logger.debug(f"Received files: {request.FILES}")
                product = form.save(commit=False)
                product.merchant = request.user
                product.save()
                messages.success(request, '产品添加成功！')
                return redirect('merchant_dashboard')
            except Exception as e:
                logger.error(f"Error saving product: {str(e)}", exc_info=True)
                messages.error(request, f"保存产品时发生错误：{str(e)}")
                return render(request, self.template_name, {'form': form})
        else:
            # Log form errors for debugging
            logger.warning(f"Form validation failed: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")

        return render(request, self.template_name, {'form': form})
@merchant_required
def edit_product(request, pk):
    product = get_object_or_404(Product, pk=pk, merchant=request.user)
    if request.method == 'POST':
        # 调试：检查上传的文件是否是列表
        uploaded_files = request.FILES.getlist('image')
        print(f"上传的文件数量: {len(uploaded_files)}")
        if len(uploaded_files) > 1:
            messages.error(request, "只能上传一个图片文件。")
            return redirect('edit_product', pk=pk)

        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product = form.save(commit=False)
            product.merchant = request.user
            product.save()
            messages.success(request, '产品更新成功！')
            return redirect('merchant_dashboard')
        else:
            print(f"表单错误: {form.errors}")
            for field, errors in form.errors.items():
                for error in errors:
                    messages.error(request, f"{field}: {error}")
    else:
        form = ProductForm(instance=product)
    return render(request, 'products/edit_product.html', {'form': form, 'product': product})


@merchant_required
def delete_product(request, pk):
    product = get_object_or_404(Product, pk=pk, merchant=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, '产品删除成功！')
        return redirect('merchant_dashboard')
    return render(request, 'products/delete_product.html', {'product': product})


@merchant_required
def merchant_orders(request):
    orders = Order.objects.filter(items__product__merchant=request.user).distinct().order_by('-created_at')
    context = {
        'orders': orders,
    }
    return render(request, 'products/merchant_orders.html', context)


from django.shortcuts import render, get_object_or_404
from .models import Product

def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)

    # specifications 是一个已经解析好的 Python 字典
    specifications = product.specifications

    # 构造包含类型信息的结构
    formatted_specifications = []
    for key, value in specifications.items():
        # 判断 value 是否是列表
        if isinstance(value, list):
            formatted_specifications.append((key, value, True))  # 值是列表
        else:
            formatted_specifications.append((key, value, False))  # 值是字符串

    return render(request, 'products/product_detail.html', {
        'product': product,
        'specifications': formatted_specifications,
    })



@merchant_required
def sales_statistics(request):
    merchant = request.user
    today = datetime.now()
    start_date = today - timedelta(days=30)

    orders = Order.objects.filter(items__product__merchant=merchant).distinct()
    total_sales = sum(order.total_price for order in orders)
    order_count = orders.count()

    category_sales = {}
    for item in OrderItem.objects.filter(product__merchant=merchant):
        category = item.product.category.name
        category_sales[category] = category_sales.get(category, 0) + item.price * item.quantity

    daily_sales = {}
    for i in range(30):
        date = (today - timedelta(days=i)).date()
        daily_sales[date] = sum(
            item.order.total_price for item in OrderItem.objects.filter(
                product__merchant=merchant,
                order__created_at__date=date
            )
        )

    plt.figure(figsize=(10, 6))
    plt.plot(list(daily_sales.keys()), list(daily_sales.values()), marker='o')
    plt.title('30天销售趋势')
    plt.xlabel('日期')
    plt.ylabel('销售额 (¥)')
    plt.grid(True)
    plt.xticks(rotation=45)
    img = io.BytesIO()
    plt.savefig(img, format='png')
    img.seek(0)
    plot_url = base64.b64encode(img.getvalue()).decode()

    context = {
        'total_sales': total_sales,
        'order_count': order_count,
        'category_sales': category_sales,
        'plot_url': plot_url,
    }
    return render(request, 'products/sales_statistics.html', context)