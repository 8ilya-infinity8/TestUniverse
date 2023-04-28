from flask import Flask, render_template, redirect, request, abort
from flask_wtf.csrf import CSRFProtect
from flask_restful import Api
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from data import db_session, users_resources, tests_resources

from data.users import User
from data.tests import Tests
from forms.user import RegisterForm, LoginForm, ProfileForm
from forms.test import CreateForm, CompleteTest
from forms.search import SearchForm

app = Flask(__name__)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'
CSRFProtect(app)

api = Api(app)

login_manager = LoginManager()
login_manager.init_app(app)


def compressor(lst):
    # преобразование списка вопросов из теста, удаление лишнего
    for question in lst:
        replacer = []
        for answer in question['answers']:
            replacer.append(answer['ans'])
        question['answers'] = replacer
        del question['add_ans']
        del question['remove_ans']
        del question['csrf_token']
    return str(lst)


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


@app.route("/", methods=['GET', 'POST'])
def index():
    # главная страница с разными тестами и поисковой строкой на ней
    search_form = SearchForm()
    if search_form.validate_on_submit():
        req = search_form.search.data
    else:
        req = ''
    db_sess = db_session.create_session()
    if current_user.is_authenticated:
        tests = db_sess.query(Tests).filter(
            (Tests.user == current_user) | (Tests.is_private is not True),
            Tests.title.like(f'%{req}%')
        )
    else:
        tests = db_sess.query(Tests).filter(
            Tests.is_private is not True,
            Tests.title.like(f'%{req}%')
        )
    users = db_sess.query(User).all()
    names = {name.id: name.name for name in users}
    return render_template("index.html", form=search_form, tests=tests, names=names)


@app.route('/login', methods=['GET', 'POST'])
def login():
    # обработка формы для входа
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login.html', message="Wrong login or password", form=form)
    return render_template('login.html', title='Authorization', form=form)


@app.route('/logout')
@login_required
def logout():
    # обработка выхода из аккаунта
    logout_user()
    return redirect("/")


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    # обработка регистрации пользователя
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if (db_sess.query(User).filter(User.email == form.email.data).first()
                or db_sess.query(User).filter(User.name == form.name.data).first()):
            return render_template('register.html', title='Регистрация',
                                   form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            about=form.about.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/login')
    return render_template('register.html', title='Регистрация', form=form)


@app.route('/profile/<string:nickname>', methods=['GET', 'POST'])
def profile(nickname):
    # обработка формы профиля, смена пароля, поиск тестов по пользователю
    form = ProfileForm()
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.name == nickname).first()
    if user:
        about = user.about
        if not about:
            about = 'нет данных'
    else:
        abort(404)
    if current_user.is_authenticated:
        tests = db_sess.query(Tests).filter(
            (Tests.user == current_user) | (Tests.is_private is not True),
            Tests.creator == user.id
        )
    else:
        tests = db_sess.query(Tests).filter(
            Tests.is_private is not True,
            Tests.creator == user.id
        )
    if form.validate_on_submit():
        if user and user.check_password(form.cur_password.data):
            user.set_password(form.new_password.data)
            db_sess.commit()
        else:
            return render_template('profile.html', nick=nickname, about=about, tests=tests,
                                   message="Wrong password", form=form)
    return render_template('profile.html', nick=nickname, tests=tests,
                           about=about, form=form)


@app.route('/create_test', methods=['GET', 'POST'])
@login_required
def create_test():
    # обработка формы по созданию теста, добавление/удаление полей в форме
    form = CreateForm()
    flag = -2
    if form.validate_on_submit():
        if 'add' in request.form:
            form.modify('add')
            flag = -1
            return render_template('create_test.html', title='Создание теста',
                                   flag=flag, form=form)
        if 'remove' in request.form:
            form.modify('remove')
            flag = -1
            return render_template('create_test.html', title='Создание теста',
                                   flag=flag, form=form)
        for i in range(len(form.tests.entries)):
            if f'tests-{i}-add_ans' in request.form:
                flag = i
                form.tests.entries[i].modify('add')
                return render_template('create_test.html', title='Создание теста',
                                       flag=flag, form=form)
            if f'tests-{i}-remove_ans' in request.form:
                flag = i
                form.tests.entries[i].modify('remove')
                return render_template('create_test.html', title='Создание теста',
                                       flag=flag, form=form)
        db_sess = db_session.create_session()
        if db_sess.query(Tests).filter(Tests.title == form.title.data).first():
            return render_template('create_test.html', title='Создание теста',
                                   flag=-1, form=form,
                                   message="Такое название уже есть")
        if len(form.key.data.split()) != len(form.tests.entries):
            return render_template('create_test.html', title='Создание теста',
                                   flag=-1, form=form,
                                   message="Количество ответов не совпадает с количеством вопросов")
        test = Tests(
            title=form.title.data,
            duration=(form.duration.data if 0 < form.duration.data < 61 else 5),
            content=compressor(form.tests.data),
            key=form.key.data,
            size=len(form.tests.entries),
            is_private=form.privacy.data,
            code=form.code.data,
            creator=current_user.id
        )
        db_sess.add(test)
        db_sess.commit()
        return redirect('/')
    return render_template('create_test.html', title='Создание теста',
                           flag=flag, form=form)


@app.route('/complete_test/<int:id>', methods=['GET', 'POST'])
def complete_test(id):
    # обработка формы для прохождения теста, сравнение с ответами, получение результата
    complete_form = CompleteTest()
    db_sess = db_session.create_session()
    test = db_sess.query(Tests).filter(Tests.id == id).first()
    title, size, duration = test.title, test.size, test.duration
    questions = eval(test.content)
    complete_form.set(len(questions))
    result = -1
    for i in range(len(questions)):
        q = questions[i]
        choices = []
        for j in range(len(q['answers'])):
            choices += [(str(j + 1), q['answers'][j])]
        complete_form.questions[i].title = q['title']
        complete_form.questions[i].variants.choices = choices
    if complete_form.validate_on_submit():
        user_answers = []
        for question in complete_form.questions.data:
            user_answers += [question['variants']]
        correct_answers = test.key.split()
        result = 0
        if len(correct_answers) < size:
            correct_answers += ['0'] * (size - len(correct_answers))
        for i in range(size):
            if user_answers[i] == correct_answers[i]:
                result += 1
    return render_template('complete_test.html', title=title, size=size,
                           result=result, percents=round(result / size * 100),
                           duration=duration, form=complete_form)


@app.route('/edit_test/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_test(id):
    # редактирование уже готового теста
    edit_form = CreateForm()
    edit_form.submit.label.text = 'Изменить'
    flag = -2
    if request.method == "GET":
        db_sess = db_session.create_session()
        test_line = db_sess.query(Tests).filter(Tests.id == id).first()
        if test_line and current_user.id in (1, test_line.creator):
            stopper1 = 1
            for q in eval(test_line.content):
                if not stopper1:
                    edit_form.modify('add')
                else:
                    stopper1 -= 1
                edit_form.tests[-1].title.data = q['title']
                stopper2 = 2
                for i in range(len(q['answers'])):
                    if not stopper2:
                        edit_form.tests[-1].modify('add')
                    else:
                        stopper2 -= 1
                    edit_form.tests[-1].answers[i].ans.data = q['answers'][i]
            edit_form.title.data = test_line.title
            edit_form.duration.data = test_line.duration
            edit_form.key.data = test_line.key
            edit_form.privacy.data = test_line.is_private
            edit_form.code.data = test_line.code
        else:
            abort(404)
    if edit_form.validate_on_submit():
        if 'add' in request.form:
            edit_form.modify('add')
            flag = -1
            return render_template('create_test.html', title='Создание теста',
                                   flag=flag, form=edit_form)
        if 'remove' in request.form:
            edit_form.modify('remove')
            flag = -1
            return render_template('create_test.html', title='Создание теста',
                                   flag=flag, form=edit_form)
        for i in range(len(edit_form.tests.entries)):
            if f'tests-{i}-add_ans' in request.form:
                edit_form.tests.entries[i].modify('add')
                flag = i
                return render_template('create_test.html', title='Создание теста',
                                       flag=flag, form=edit_form)
            if f'tests-{i}-remove_ans' in request.form:
                edit_form.tests.entries[i].modify('remove')
                flag = i
                return render_template('create_test.html', title='Создание теста',
                                       flag=flag, form=edit_form)
        db_sess = db_session.create_session()
        test_line = db_sess.query(Tests).filter(Tests.id == id).first()
        if (test_line.title != edit_form.title.data and
                db_sess.query(Tests).filter(Tests.title == edit_form.title.data).first()):
            return render_template('create_test.html', title='Создание теста',
                                   flag=-1, form=edit_form,
                                   message="Такое название уже есть")
        if len(edit_form.key.data.split()) != len(edit_form.tests.entries):
            return render_template('create_test.html', title='Создание теста',
                                   flag=-1, form=edit_form,
                                   message="Количество ответов не совпадает с количеством вопросов")
        if test_line and current_user.id in (1, test_line.creator):
            test_line.title = edit_form.title.data
            test_line.duration = edit_form.duration.data
            test_line.content = compressor(edit_form.tests.data)
            test_line.key = edit_form.key.data
            test_line.is_private = edit_form.privacy.data
            test_line.code = edit_form.code.data
            test_line.size = len(edit_form.tests.entries)
            db_sess.commit()
            return redirect('/')
        else:
            abort(404)
    return render_template('create_test.html',
                           title='Редактирование теста',
                           flag=flag,
                           form=edit_form
                           )


@app.route('/delete_test/<int:id>', methods=['GET', 'POST'])
@login_required
def delete_test(id):
    # удаление созданного ранее теста
    db_sess = db_session.create_session()
    test_line = db_sess.query(Tests).filter(Tests.id == id,
                                            (Tests.creator == current_user.id) | (current_user.id == 1)
                                            ).first()
    if test_line:
        db_sess.delete(test_line)
        db_sess.commit()
    else:
        abort(404)
    return redirect('/')


def main():
    db_session.global_init("db/testing_system.db")
    api.add_resource(users_resources.UsersListResource, '/api/v2/users')
    api.add_resource(users_resources.UsersResource,
                     '/api/v2/users/<int:user_id>')
    api.add_resource(tests_resources.TestsListResource, '/api/v2/tests')
    api.add_resource(tests_resources.TestsResource,
                     '/api/v2/tests/<int:test_id>')
    app.run()


if __name__ == '__main__':
    main()
