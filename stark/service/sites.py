from django.conf.urls import url
from django.urls import reverse
from django import forms
from stark.utils.page import MyPage
from django.db.models import Q
from django.utils.safestring import mark_safe
from django.db.models.fields.related import ManyToManyField
from django.shortcuts import HttpResponse, render, redirect


# 将展示页面封装成一个类
class ShowList(object):
    # 初始化
    def __init__(self, config_obj, data_list, request):
        self.config_obj = config_obj  # 当前查看表的配置类对象
        self.data_list = data_list
        self.request = request

        # 分页
        self.pagination = MyPage(request.GET.get("page", 1),self.data_list.count(),request,per_page_data=3)
        self.page_queryset = self.data_list[self.pagination.start:self.pagination.end]

    # actions操作
    def get_new_actions(self):
        temp = []
        temp.extend(self.config_obj.actions)
        temp.append(self.config_obj.patch_delete)
        new_actions = []
        print(self.config_obj.actions)   # [patch_init,patch_delete]这个对象
        print(temp)
        for func in temp:
            new_actions.append({
                "text":func.desc,
                "name":func.__name__
            })
        # print(new_actions)
        # [{'text': '价格初始化', 'name': 'patch_init'}, {'text': '批量删除', 'name': 'patch_delete'},
        return new_actions

    # 表头函数
    def get_headers(self):
        # 构建表头
        # 想要的形式是这种形式header_list=["书籍名称","价格"]
        header_list = []
        for field_or_func in self.config_obj.new_list_display():  # 依然循环["title","price","publish",edit]
            # 如果是函数的话这样
            if callable(field_or_func):
                # 如果是函数
                val = field_or_func(self.config_obj, is_header=True)
            else:
                # # 如果只是单纯的字符串字段
                # 如果这个字段是__str__
                if field_or_func == "__str__":
                    val = self.config_obj.model._meta.model_name.upper()
                    print(val)
                else:
                    # 获取到的是字段里边的verbose_name，如果没这个就是默认的表明
                    field_obj = self.config_obj.model._meta.get_field(field_or_func)
                    val = field_obj.verbose_name
            header_list.append(val)
        return header_list

    # 表单数据部分
    def get_body(self):
        # 构建数据表单部分
        new_data_list = []  # 先创建一个外层列表，在这个列表里边放小列表
        for obj in self.page_queryset:  # 循环 这个对应的列表，Queryset[book1,book2]
            temp = []  # 小列表
            for field_or_func in self.config_obj.new_list_display():
                # 循环的就是你display中的东西，不仅有字段相对应的字符串，还可能有自定义的函数["title","price","publish",edit]
                # 故要做判断,callable是判断是否是函数，
                if callable(field_or_func):
                    # 如果是函数，则执行这个函数
                    val = field_or_func(self.config_obj, obj)
                else:
                    # 如果是字符串，
                    # 如果是多对多字段，先导入一个from django.db.models.fields.related import ManyToManyField
                    # 这个是获取出来字段，
                    try:
                        field_obj = self.config_obj.model._meta.get_field(field_or_func)
                        print(field_obj)
                        # app01.Book.title
                        # app01.Book.price
                        # app01.Book.publish
                        # app01.Book.authors
                        if isinstance(field_obj, ManyToManyField):
                            # 然后判断哪个字段是多对多字段，isinstance就是判断是否是多对多字段
                            # 如果是就要用.all()全部获取出来，
                            rel_data_list = getattr(obj, field_or_func).all()
                            print(rel_data_list)
                            # 获取出来每本书对应的作者这个对象
                            # <QuerySet [<Author: 沈巍>, <Author: 蓝忘机>]>
                            l = [str(item) for item in rel_data_list]
                            # 经过for循环，并且转成字符串，用|隔开
                            val = "|".join(l)
                            # 如果这个字段在links里边，获取一下路径，生成a标签
                            if field_or_func in self.config_obj.list_display_links:
                                _url = self.config_obj.get_change_url(obj)
                                val = mark_safe("<a href='%s'>%s</a>"%(_url, val))
                        else:
                            # 如果不是多对多字段，就直接获取就行
                            val = getattr(obj, field_or_func)  # 反射
                            # 如果这个字段在links里边，获取一下路径，生成a标签
                            if field_or_func in self.config_obj.list_display_links:
                                _url = self.config_obj.get_change_url(obj)
                                val = mark_safe("<a href='%s'>%s</a>"%(_url, val))
                    except Exception as e:
                        val = getattr(obj, field_or_func)  # 反射
                # 都添加到小列表中
                temp.append(val)
            # 添加到大列表中
            new_data_list.append(temp)
        return new_data_list





class ModelStark(object):
    """
    默认配置类
    """
    list_display = ["__str__"]
    list_display_links = []
    search_fields = []
    actions = []
    model_form_class = []

    def __init__(self, model):
        self.model = model
        # 方便调用
        self.model_name = self.model._meta.model_name
        self.app_label = self.model._meta.app_label

    # 批量操作
    def patch_delete(self, request, queryset):
        queryset.delete()

    patch_delete.desc = "批量删除"

    # 反向解析当前查看表的增删改查的url
    def get_list_url(self):
        url_name = "%s_%s_list" % (self.app_label, self.model_name)
        _url = reverse(url_name)
        return _url

    def get_add_url(self):
        url_name = "%s_%s_add" % (self.app_label, self.model_name)
        _url = reverse(url_name)
        return _url

    def get_change_url(self, obj):
        url_name = "%s_%s_change" % (self.app_label, self.model_name)
        _url = reverse(url_name, args=(obj.pk,))
        return _url

    def get_delete_url(self, obj):
        url_name = "%s_%s_delete" % (self.app_label, self.model_name)
        _url = reverse(url_name, args=(obj.pk,))
        return _url

    # 默认操作函数
    def edit(self, obj=None, is_header=False):
        if is_header:
            return "操作"
        return mark_safe("<a href='%s' class='btn btn-warning btn-sm'>编辑</a>" % self.get_change_url(obj))

    def delete(self, obj=None, is_header=False):
        if is_header:
            return "删除"
        return mark_safe("<a href='%s' class='btn btn-danger btn-sm'>删除</a>" % self.get_delete_url(obj))

    def checkbox(self, obj=None, is_header=False):
        if is_header:
            return "选择"
        return mark_safe("<input type='checkbox' name='pk_list' value=%s>" % obj.pk)

    # 视图函数
    # 定义一个新的列表，既存放字段，有存放edit，delete，checkbox
    def new_list_display(self):
        temp = []
        # 把我原来的list_display数据添加进去
        temp.extend(self.list_display)
        # 把checkbox插入在第一位
        temp.insert(0, ModelStark.checkbox)
        # 继续往后添加edit字符串
        # 我们因为增加了一个link属性，所以就在这里判断一下，
        # 如果有links这个属性，我们就不添加增加这个属性了，如果没有的话，我们增加
        if not self.list_display_links:
            temp.append(ModelStark.edit)
        # 继续往后添加删除字符串
        temp.append(ModelStark.delete)
        return temp

    # 搜索框
    def get_search_condition(self, request):
        # 获取数据
        val = request.GET.get("a")
        search_condition = Q()
        # 如果有数据
        if val:
            search_condition.connector = "or"
            for field in self.search_fields:
                # print("self.search_fields", self.search_fields)  # ['title']
                # 固定写法  __icontains就是包含的意思
                search_condition.children.append((field + "__icontains", val))
                # print(search_condition)
        return search_condition

    # 查看视图函数,将此里边的函数封装成一个函数
    def listview(self, request):
        # print(self)  # 当前访问模型表的配置类对象
        # print(self.model)  # 当前访问模型表
        # print(self.list_display)
        if request.method == "POST":
            # 获取到我们选中的id，即对象
            pk_list = request.POST.getlist("pk_list")
            # 看id是否在pk_list中
            queryset = self.model.objects.filter(pk__in=pk_list)
            # 或取到这个名字即函数名
            action = request.POST.get("action")
            # 因为获取的是字符串，所以要用反射，self表示配置类对象
            action=getattr(self,action)
            print(action)
            action(request,queryset)
        data_list = self.model.objects.all()
        # 在这个页面上增加一个增加数据的按钮，跳转到那个路径
        add_url = self.get_add_url()
        # 获取搜索条件对象
        search_condition = self.get_search_condition(request)
        # 数据过滤展示
        data_list = data_list.filter(search_condition)
        # 分页展示
        showlist = ShowList(self, data_list, request)

        return render(request, "list_view.html", locals())

    # modelform
    def get_model_form(self):
        if self.model_form_class:
            # 如果不是使用的默认类,就是model_form_class不为空，有自己的配置类
            return self.model_form_class
        else:
            # 如果使用的是默认配置类的modelform
            class ModelFormClass(forms.ModelForm):
                class Meta:
                    # 就是关联的表名称
                    model = self.model
                    # 就是显示关联的字段名
                    fields = "__all__"

            return ModelFormClass

    # 编辑试图函数
    def addview(self, request):

        ModelFormClass = self.get_model_form()
        if request.method == "POST":
            # 获取数据
            form_obj = ModelFormClass(request.POST)
            # 校验数据
            if form_obj.is_valid():
                form_obj.save()  # 记得保存
                # 跳转到首页
                return redirect(self.get_list_url())
            # 这个返回是为了显示错误信息
            return render(request, "add_view.html", locals())
        # 实例化
        form_obj = ModelFormClass()
        return render(request, "add_view.html", locals())

    # 更改视图函数
    def changeview(self, request, id):
        ModelFormClass = self.get_model_form()
        # 选择要编辑的对象
        edit_obj = self.model.objects.get(pk=id)
        if request.method == "POST":
            form_obj = ModelFormClass(request.POST, instance=edit_obj)
            if form_obj.is_valid():
                form_obj.save()
                return redirect(self.get_list_url())
            return render(request,"change_view.html",locals())
        # 记得instance
        form_obj = ModelFormClass(instance=edit_obj)
        return render(request,"change_view.html",locals())

    # 删除视图函数
    def delview(self, request, id):
        if request.method == "POST":
            # 获取到所选择的对象
            self.model.objects.filter(pk=id).delete()
            return redirect(self.get_list_url())
        list_url = self.get_list_url()
        return render(request, "delete_view.html", locals())

    # 设计url，用反向解析，
    def get_urls(self):
        model_name = self.model._meta.model_name
        app_label = self.model._meta.app_label
        temp = [
            url(r"^$", self.listview, name="%s_%s_list" % (app_label, model_name)),
            url(r"add/$", self.addview, name="%s_%s_add" % (app_label, model_name)),
            url(r"(\d+)/change/$", self.changeview, name="%s_%s_change" % (app_label, model_name)),
            url(r"(\d+)/delete/$", self.delview, name="%s_%s_delete" % (app_label, model_name)),

        ]
        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


class AdminSite(object):
    """
        stark组件的全局类
    """

    def __init__(self):
        self._registry = {}

    def register(self, model, admin_class=None):
        # 设置配置类
        if not admin_class:
            admin_class = ModelStark
        self._registry[model] = admin_class(model)

    def get_urls(self):
        temp = []
        for model, config_obj in self._registry.items():
            model_name = model._meta.model_name
            app_label = model._meta.app_label
            temp.append(url(r"%s/%s/" % (app_label, model_name), config_obj.urls))
            # config_obj 获取的就是每个for循环中的BookConfig(Book)，publish，author遍历的对象
        return temp

    @property
    def urls(self):
        return self.get_urls(), None, None


site = AdminSite()
