from django import forms
from .models import Product, Category
import json

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ['category', 'name', 'description', 'price', 'stock', 'specifications', 'image']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 4}),
            'specifications': forms.Textarea(attrs={'rows': 3}),
            'image': forms.ClearableFileInput(attrs={'accept': 'image/png,image/jpeg'}),  # Restrict to single file
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter categories to only leaf nodes (no children) to avoid selecting parent categories
        self.fields['category'].queryset = Category.objects.filter(parent__isnull=True)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            if image.size > 5 * 1024 * 1024:  # 5MB limit
                raise forms.ValidationError("图片大小不能超过5MB")
            if not image.name.lower().endswith(('.png', '.jpg', '.jpeg')):
                raise forms.ValidationError("仅支持PNG和JPG格式")
        return image

    def clean_specifications(self):
        specs = self.cleaned_data.get('specifications')
        try:
            # Ensure specifications is valid JSON
            if isinstance(specs, str):
                specs = json.loads(specs)
            if not isinstance(specs, dict):
                raise forms.ValidationError("规格必须是有效的JSON对象")
        except json.JSONDecodeError:
            raise forms.ValidationError("规格必须是有效的JSON格式")
        return specs

    def clean_price(self):
        price = self.cleaned_data.get('price')
        if price <= 0:
            raise forms.ValidationError("价格必须大于0")
        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')
        if stock < 0:
            raise forms.ValidationError("库存数量不能为负")
        return stock

    def clean_name(self):
        name = self.cleaned_data.get('name')
        if len(name.strip()) < 3:
            raise forms.ValidationError("商品名称必须至少包含3个字符")
        return name.strip()