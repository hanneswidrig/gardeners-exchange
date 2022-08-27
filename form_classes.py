from flask_wtf import FlaskForm
from flask_wtf.file import FileRequired
from wtforms import (
    StringField,
    IntegerField,
    SelectField,
    DecimalField,
    DateField,
    BooleanField,
    FileField,
    SubmitField,
    TextAreaField,
    PasswordField
)
from wtforms.validators import Email, Length, DataRequired, NumberRange, EqualTo


class BuyForm(FlaskForm):
    quantity = IntegerField(
        'Quantity to buy',
        validators=[NumberRange(min=1, message="Must buy more than 0.")])
    submit = SubmitField('Pay')


class AddListingForm(FlaskForm):
    title = StringField(
        'Title', validators=[Length(min=1, message="A title is required.")])
    photo = FileField(
        'Product Photo',
        validators=[FileRequired(message="Please choose an image to upload.")])
    description = TextAreaField(
        'Description',
        validators=[Length(min=1, message="A description is required.")])
    original_quantity = IntegerField(
        'Quantity For Sale',
        validators=[NumberRange(min=1, message="A quantity is required.")])
    unit_type = StringField(
        'Measurement',
        validators=[Length(min=1, message="A measurement is required.")])
    price_per_unit = DecimalField(
        'Price Per Unit',
        validators=[NumberRange(min=0.01, message="A price is required.")])
    category_id = SelectField(
        'Category',
        choices=[(1, 'Vegetable'), (2, 'Fruit'), (3, 'Meat'), (4, 'Cheese')],
        coerce=int)
    is_tradeable = BooleanField('Should this product be tradeable?')
    date_harvested = DateField('Date Harvested', format="%Y-%m-%d")
    submit = SubmitField('Add')


class LoginForm(FlaskForm):
    email = StringField('E-mail Address', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')


class MemberForm(FlaskForm):
    email = StringField('Email', validators=[Email()])
    first_name = StringField('First Name', validators=[Length(min=1, max=40)])
    last_name = StringField('Last Name', validators=[Length(min=1, max=40)])
    address_street = StringField(
        'Street Address', validators=[Length(min=1, max=128)])
    address_city = StringField('City', validators=[Length(min=1, max=128)])
    address_state = SelectField('State', coerce=int)
    address_zipcode = IntegerField(
        'ZIP Code', validators=[NumberRange(min=00000, max=99999)])

    photo = FileField('Profile Picture')
    bio = TextAreaField('Biography', validators=[Length(min=1, max=250)])
    password = PasswordField(
        'Password',
        [DataRequired(),
         EqualTo('confirm', message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Create Account')
