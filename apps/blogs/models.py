from django.db import models
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils.text import slugify
from ckeditor_uploader.fields import RichTextUploadingField

class Category(models.Model):
    title = models.CharField(max_length=30, unique=True)
   
    class Meta:
        ordering =['title']
        verbose_name_plural = "categories"        
                                                

    def __str__(self):                          
        return self.title                         
class Tag(models.Model):
    t_name = models.CharField(max_length=30,unique=True)
    # blog = models.ForeignKey(
    #     Blog,
    #     on_delete=models.CASCADE,
    #     related_name="tags",
    #     related_query_name="tag",
    # )
    class Meta:
        ordering =['t_name']
        verbose_name_plural = "tags"        
                                                

    def __str__(self):                          
        return self.t_name                         


class Blog(models.Model):
   
    title =models.CharField(max_length=255)
    content = RichTextUploadingField()
    count = models.IntegerField(default=0)
    category =models.ForeignKey(Category,on_delete=models.SET_NULL, null=True)
    cover_image =models.ImageField(upload_to='media/blog',null=True)
    author = models.ForeignKey(User,on_delete=models.SET_NULL, null=True)
    tags=models.ManyToManyField(Tag)
    slug =  models.SlugField(null=True, max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.slug = slugify(self.title)
        super(Blog, self).save(*args, **kwargs)


    def get_absolute_url(self):
        return reverse("blog_detail", kwargs={"slug": self.slug,"category": self.category})

    