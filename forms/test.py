from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, BooleanField, IntegerField, FieldList, FormField, RadioField
from wtforms.validators import DataRequired


class CreateAnswer(FlaskForm):
    ans = StringField()


class CreateQuestion(FlaskForm):
    title = StringField('Вопрос')
    answers = FieldList(FormField(CreateAnswer), min_entries=2, validators=[DataRequired()])
    add_ans = SubmitField('добавить ответ')
    remove_ans = SubmitField('убрать ответ')

    def modify(self, mode='add'):
        ln = len(self.answers.entries)
        if mode == 'add':
            if ln < 16:
                self.answers.append_entry(FormField(CreateAnswer))
        else:
            if ln > 2:
                self.answers.pop_entry()


class CreateForm(FlaskForm):
    title = StringField('Название теста', validators=[DataRequired()])
    duration = IntegerField('Примерное время прохождения (в минутах, от 1 до 60)', default=5)
    privacy = BooleanField('Доступность только по спец коду', default=False)
    code = StringField('Спец код', default='TOP4SECRET')
    tests = FieldList(FormField(CreateQuestion), min_entries=1, validators=[DataRequired()])
    add = SubmitField('добавить вопрос')
    remove = SubmitField('убрать вопрос')
    key = StringField('Ответы в виде чисел через пробел')
    submit = SubmitField('Создать')

    def modify(self, mode='add'):
        if mode == 'add':
            self.tests.append_entry(FormField(CreateQuestion))
        else:
            if len(self.tests.entries) > 1:
                self.tests.pop_entry()


class CompleteQuestion(FlaskForm):
    title = 'title'
    variants = RadioField('var', choices=[(i, str(i)) for i in range(16)], default='0')


class CompleteTest(FlaskForm):
    questions = FieldList(FormField(CompleteQuestion))
    submit = SubmitField('завершить')

    def set(self, n):
        while len(self.questions.entries) < n:
            self.questions.append_entry(FormField(CompleteQuestion))
