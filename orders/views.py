from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from .models import Order, OrderItem
from products.models import Product

@login_required
def create_order(request):
    if request.method == 'POST':
        product_id = request.POST.get('product_id')
        quantity = int(request.POST.get('quantity', 1))
        is_buy_now = request.POST.get('action') == 'buy_now'
        if not product_id:
            messages.error(request, '产品ID缺失，请重新尝试。')
            return redirect('home')
        product = get_object_or_404(Product, pk=product_id)
        if product.stock < quantity:
            messages.error(request, '库存不足！')
            return redirect('product_detail', pk=product_id)
        order, created = Order.objects.get_or_create(
            user=request.user,
            status='待支付'  # 改为中文
        )
        if is_buy_now and not created:
            order.items.all().delete()
        order_item, created = OrderItem.objects.get_or_create(
            order=order,
            product=product,
            defaults={'quantity': quantity, 'price': product.price}
        )
        if not created:
            order_item.quantity = quantity
            order_item.save()
        order.total_price = sum(item.get_total() for item in order.items.all())
        order.save()
        product.stock -= quantity
        product.save()
        messages.success(request, '商品已{}成功！'.format('购买' if is_buy_now else '加入订单'))
        if is_buy_now:
            return redirect('order_detail', pk=order.id)
        else:
            return redirect('order_list')
    return redirect('product_detail', pk=product_id) if product_id else redirect('home')

@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == 'POST':
        if request.POST.get('action') == 'cancel':
            order.status = '已取消'
            for item in order.items.all():
                item.product.stock += item.quantity
                item.product.save()
            order.save()
            messages.success(request, '订单已取消！')
            return redirect('order_list')
        elif request.POST.get('action') == 'confirm_receipt':
            if order.status == '已发货':
                order.status = '已完成'
                order.save()
                messages.success(request, '确认收货成功！')
                return redirect('order_detail', pk=order.id)
            messages.error(request, '订单状态不支持确认收货！')
            return redirect('order_detail', pk=order.id)
    context = {'order': order}
    return render(request, 'orders/order_detail.html', context)

@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    context = {'orders': orders}
    return render(request, 'orders/order_list.html', context)

@login_required
def pay_order(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    if request.method == 'POST':
        if order.status == '待支付':
            order.status = '已支付'
            order.save()
            messages.success(request, '支付成功！')
            return JsonResponse({'status': 'success', 'message': '支付成功！订单状态已更新。'})
        return JsonResponse({'status': 'error', 'message': '订单状态不支持支付！'})
    return redirect('order_detail', pk=pk)

@login_required
def ship_order(request, pk):
    order = get_object_or_404(Order, pk=pk)
    if request.user == order.items.first().product.merchant and order.status == '已支付':
        order.status = '已发货'
        order.save()
        messages.success(request, '订单已发货！')
        return redirect('merchant_orders')
    messages.error(request, '无权操作或订单状态错误！')
    return redirect('merchant_orders')