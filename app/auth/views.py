# -*- coding: utf-8 -*-

from flask import render_template, redirect, request, url_for, flash
from . import auth
from flask_login import login_user, login_required, logout_user, current_user
from ..models import User
from .forms import LoginForm, RegistrationForm, ChangePasswordForm, ResetPasswordForm, ResetPasswordEmailForm
from app import db
from ..email import send_email
from ..decorators import admin_required, permission_required


@auth.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user is not None and user.verify_password(form.password.data):
            login_user(user, form.remember_me.data)
            return redirect(request.args.get('next') or url_for('main.index'))
        flash('用户名或密码错误！')
    return render_template('auth/login.html', form=form)


@auth.route('/logout')
@login_required
def logout():
    logout_user()
    flash("你已退出登录！")
    return redirect(url_for('main.index'))


@auth.route('/register', methods=['GET', 'POST'])
def register():
    form = RegistrationForm()
    username = request.args.get('username')
    if username:
        form.username.data = username
    if form.validate_on_submit():
        user = User(email=form.email.data, username=form.username.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()
        token = user.generate_confirmation_token()
        send_email(user.email, '确认注册', 'auth/email/confirm', user=user, token=token)
        flash('一封确认邮件已经发送给您，请点击邮件中的链接完成注册。')
        return redirect(url_for('auth.login'))
    return render_template('auth/register.html', form=form)


@auth.route('/confirm/<token>', methods=['GET', 'POST'])
@login_required
def confirm(token):
    if current_user.confirmed:
        return redirect(url_for('main.index'))
    if current_user.confirm(token):
        flash("注册完成。")
    else:
        flash("当前链接已失效，请重新发送邮件")
        return redirect(url_for('.unconfirmed'))
    return redirect(url_for('main.index'))


@auth.before_app_request
def before_request():
    if current_user.is_authenticated:
        current_user.ping()
        if not current_user.confirmed and request.endpoint[:5] != 'auth.' and request.endpoint != 'static':
            return redirect(url_for('auth.unconfirmed'))


@auth.route('/unconfirmed')
def unconfirmed():
    if current_user.is_anonymous or current_user.confirmed:
        return redirect(url_for('main.index'))
    return render_template('auth/unconfirmed.html', user=current_user)


@auth.route('/confirm')
@login_required
def resend_confirmation():
    token = current_user.generate_confirmation_token()
    send_email(current_user.email, '确认账户', 'auth/email/confirm', user=current_user, token=token)
    flash('一封新的邮件已经发送至您的邮箱。')
    return redirect(url_for('main.index'))


@auth.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.verify_password(form.old_password.data):
            current_user.password = form.new_password.data
            db.session.add(current_user)
            flash('密码更改成功')
        else:
            flash('旧密码不正确，请重新输入')
            return redirect(url_for('.change_password'))
        return redirect(url_for('main.index'))
    return render_template('auth/change_password.html', form=form)


@auth.route('/reset_password', methods=['GET', 'POST'])
def reset_password():
    form = ResetPasswordEmailForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            token = user.generate_confirmation_token()
            send_email(user.email, '重置密码', 'auth/email/reset', user=current_user, token=token)
            flash('一封邮件已经发送至您的邮箱。')
            return redirect(url_for('main.index'))
        else:
            flash('当前用户不存在，请检查邮箱。')
        return redirect(url_for('.reset_password'))
    return render_template('auth/reset_password.html', form=form)


@auth.route('/reset_password/<token>', methods=['GET', 'POST'])
@login_required
def confirm_password(token):
    if current_user.confirm(token):
        form = ResetPasswordForm()
        if form.validate_on_submit():
            current_user.password = form.new_password.data
            flash('密码修改成功。')
            return redirect(url_for('main.index'))
        return render_template('auth/reset_password.html', form=form)

    else:
        flash('当前链接已失效，请重新发送邮件')
        return redirect(url_for('auth.login'))
