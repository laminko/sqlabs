# -*- coding: utf-8 -*-
# This plugins is licensed under the MIT license: http://www.opensource.org/licenses/mit-license.php
# Authors: Kenji Hosoda <hosoda@s-cubism.jp>
from gluon import *
from gluon.storage import Storage, Messages

class CommentBox(object):
    
    def __init__(self, db):
        self.db = db
        
        settings = self.settings = Storage()
        
        settings.oncomment = None
        ##EDEFF4
        settings.select_fields = []
        settings.select_attributes = {}
        settings.headers = []
        settings.content = lambda row: row
        settings.view_all_content = lambda total: A(
                                        current.T('View all %s comments') % total, _href='#', 
                                        _class='plugin_comment_box_view_all')
        settings.footers = [TEXTAREA('', _placeholder=current.T('Write a comment..'),
                                  _rows=1, _class='plugin_comment_box_add')]
        settings.tooltip = LABEL('X', _class='plugin_comment_box_remove')
        settings.limit = 2
        
        settings.table_comment_name = 'comment'
        settings.table_comment = None
        
        messages = self.messages = Messages(current.T)
        messages.record_created = 'Record Created'
        messages.record_deleted = 'Record Deleted'
        
    def define_tables(self, table_target_name, table_user_name, 
                      migrate=True, fake_migrate=False):
        db, settings = self.db, self.settings
        
        if not settings.table_comment_name in db.tables:
            settings.table_comment = db.define_table(
                settings.table_comment_name,
                Field('target', 'reference %s' % table_target_name),
                Field('user', 'reference %s' % table_user_name),
                Field('body', 'text'),
                Field('created_on', 'datetime', default=current.request.now),
                migrate=migrate, fake_migrate=fake_migrate)
                
    def add_comment(self, user_id, target_id, body):
        db, settings, table_comment = self.db, self.settings, self.settings.table_comment
        table_comment.insert(target=target_id,
                     user=user_id,
                     body=body)
        if settings.oncomment:
            settings.oncomment(target_id, user_id, current.request.now)
            
    def remove_comment(self, user_id, comment_id):
        db, table_comment = self.db, self.settings.table_comment
        
        if db(table_comment.id==comment_id)(table_comment.user==user_id).count():
            db(table_comment.id==comment_id).delete()
        else:
            raise ValueError
            
    def comments(self, target_id):
        db, table_comment = self.db, self.settings.table_comment
        return db(table_comment.target==target_id)
        
    def element(self, user_id, target_id, view_all=False):  
        settings = self.settings
        _id = 'plugin_comment_box__%s__%s' % (user_id, target_id)
            
        settings.select_attributes.update(
            limitby=None if view_all else (0, settings.limit+1),
            orderby=~settings.table_comment.id)
        records = self.comments(target_id).select(
            *settings.select_fields, **settings.select_attributes
        )
        elements = []
        
        elements[:0] = settings.headers
            
        if not view_all and len(records) > settings.limit:
            total = self.comments(target_id).count()
            elements.append(LI(settings.view_all_content(total)))
            records = records[:settings.limit]
        
        for record in reversed(records):
            content = settings.content(record)
            if settings.table_comment_name in record:
                _user_id = record[settings.table_comment].user
                _comment_id = record[settings.table_comment].id
            else:
                _user_id = record.user
                _comment_id = record.id
            if settings.tooltip and str(_user_id) == str(user_id):
                content = DIV(DIV(settings.tooltip, 
                                  _class='plugin_comment_box_tooltip', 
                                  _style='float:right;visibility:hidden;'), 
                              DIV(content, _style='display:table-cell;padding-right:5px;'))
            elements.append(LI(content, 
                               _class='plugin_comment_box_comment', 
                               _id='plugin_comment_box_comment__%s' % _comment_id))
        
        elements.extend(settings.footers)
        
        return DIV(UL(*elements), _id=_id, _class='plugin_comment_box')
    
    def process(self):
        settings = self.settings
        form = FORM(INPUT(_type='hidden', _name='form_id'),
                    INPUT(_type='hidden', _name='target_id'),
                    INPUT(_type='hidden', _name='user_id'),
                    INPUT(_type='hidden', _name='action'),
                    INPUT(_type='hidden', _name='comment_id'),
                    INPUT(_type='hidden', _name='body'),
                    INPUT(_type='hidden', _name='view_all'))
        if form.accepts(current.request.vars, current.session):
            user_id, target_id = form.vars.user_id, form.vars.target_id
            view_all = True if form.vars.view_all == 'true' else False
            if form.vars.action == 'add':
                current.response.flash = self.messages.record_created
                self.add_comment(user_id, target_id, form.vars.body)
            elif form.vars.action == 'remove':
                current.response.flash = self.messages.record_deleted
                self.remove_comment(user_id, form.vars.comment_id)
            elif form.vars.action == 'view_all':
                view_all = True
            else:
                raise ValueError
                 
            current.response.js = """
jQuery('#%(form_id)s').find('input[name=_formkey]').val('%(formkey)s');
""" % dict(form_id=form.vars.form_id, formkey=form.formkey)
            raise HTTP(200, self.element(user_id, target_id, view_all))
            
        import uuid
        _form_id = str(uuid.uuid4())
        form.attributes['_id'] = _form_id
        
        script = SCRIPT("""
(function($) {$(function(){
var form = $('#%(form_id)s');
function set_inputs(items) {
    for (k in items) {form.children('input[name='+k+']').attr('value', items[k]);}
}
function post_form(el_id) {
    $('.flash').hide().html(''); web2py_ajax_page('post', '', form.serialize(), el_id);
}
function is_view_all(el) {
    return !el.find('.plugin_comment_box_view_all').length
}
function add(self) {
    var el = $(self).closest('.plugin_comment_box'),
        el_id = el.attr('id'),
        el_id_parts = el_id.split('__'),
        user_id = el_id_parts[1],
        target_id = el_id_parts[2],
        body = el.find('textarea').val();  
    set_inputs({form_id:'%(form_id)s', user_id:user_id, target_id: target_id, 
                action:'add', body: body, view_all:is_view_all(el)});
    post_form(el_id);
}
$('.plugin_comment_box_add').live('keypress', function(e){
    if (this.tagName=='TEXTAREA' && e.keyCode==13 && !e.shiftKey){
        add(this); return false;
    }
}).live('click', function(e){
    if (this.tagName=='INPUT') {
        add(this); return false;
    }
});
$('.plugin_comment_box_remove').live('click', function(e){
    var el = $(this).closest('.plugin_comment_box'),
        el_id = el.attr('id'),
        el_id_parts = el_id.split('__'),
        user_id = el_id_parts[1],
        target_id = el_id_parts[2],
        comment_el = $(this).closest('.plugin_comment_box_comment'),
        comment_id = comment_el.attr('id').split('__')[1];
    set_inputs({form_id:'%(form_id)s', user_id:user_id, target_id: target_id, 
                action:'remove', comment_id: comment_id, view_all:is_view_all(el)});
    post_form(el_id);
    return false;
});
$('.plugin_comment_box_comment').live({
    mouseenter:function(e){
        $(this).find('.plugin_comment_box_tooltip').css('visibility', 'visible');
    }, mouseleave:function(e){
        $(this).find('.plugin_comment_box_tooltip').css('visibility', 'hidden');
    }
});
$('.plugin_comment_box_view_all').live('click', function() {
    var el = $(this).closest('.plugin_comment_box'),
        el_id = el.attr('id'),
        el_id_parts = el_id.split('__'),
        user_id = el_id_parts[1],
        target_id = el_id_parts[2];
    set_inputs({form_id:'%(form_id)s', user_id:user_id, target_id: target_id, 
                action:'view_all'});
    post_form(el_id);
    return false;
});
});})(jQuery);""" % dict(form_id=_form_id))
        form.components.append(script)
            
        return form