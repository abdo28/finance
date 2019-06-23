import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finance.db")



@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id


    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("Missing username", 400)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("Missing password", 400)

        elif not request.form.get("confirmation"):
            return apology("Missing password (again)", 400)

        if not request.form.get("password")==request.form.get("confirmation"):
            return apology("Do not match", 400)

        hashed = generate_password_hash(request.form.get("password"))

        result = db.execute("INSERT INTO users (username , hash) VALUES (:username , :hashed)" , username = request.form.get("username") , hashed = hashed  )
        if not result :
            return apology("The username exist", 400)

        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))
        session["user_id"] = rows[0]["id"]

        return redirect("/")
    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
    """Get stock quote."""
    if request.method == "POST":
        if not request.form.get("symbol"):
            return  apology("You must provide the stock symbol",400)
        quote = lookup(request.form.get("symbol"))
        if not quote:
             return apology("Invalid symbol",400)
        return render_template("quoted.html", inc = quote["name"] , sy =quote["symbol"]  , co = usd(quote["price"]) )
    else:
        return render_template("quote.html")

@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
    """Buy shares of stock"""
    if request.method == "POST":

        if not request.form.get("symbol")  :
            return  apology("You must provide the stock symbol",400)

        if not request.form.get("shares")   :#and not (request.form.get("shares")).isdigit():
            return  apology("You must provide the number of stocks",400)
        if (not request.form.get("shares") or not request.form.get("shares").isdigit()or float(request.form.get("shares")) < 0):
            return apology("must specify a non negative number of shares to sell", 400)

        buy = lookup(request.form.get("symbol"))
        if not buy:
             return apology("Invalid symbol",400)

        rows = db.execute("SELECT * FROM users WHERE id = :ide", ide = session["user_id"] )

        minus = float(request.form.get("shares") )* buy["price"]
        if minus > rows[0]["cash"] :
            return apology("You can't buy those stocks",400)

        db.execute("UPDATE users SET cash = cash - :minus WHERE id = :idi", minus = minus , idi = session["user_id"] )

        db.execute("INSERT INTO history (userid , symbol , shares , price) VALUES (:us , :sy , :sh , :pr)", us = session["user_id"],sy = request.form.get("symbol") , sh = int(request.form.get("shares")) , pr = buy["price"]   )
        return redirect("/")
    else :
        return render_template("buy.html")


@app.route("/")
@login_required
def index():
    """Show portfolio of stocks"""
    rows = db.execute("SELECT * FROM history WHERE userid = :ide", ide = session["user_id"] )
    data = {}

    sume = 0
    for row in range(len(rows)):
        if rows[row]["symbol"] in data.keys():
            data[rows[row]["symbol"]][0]=data[rows[row]["symbol"]][0]+ rows[row]["shares"]
        else:
            data[rows[row]["symbol"]] = [int(rows[row]["shares"]),rows[row]["price"],0.0 ]
    for k , v in data.items():
        v[2]= v[0]*v[1]
        sume = sume + v[2]
    real = 10000.0 - sume
    for k , v in data.items():
        v[1]=usd(v[1])
        v[2]=usd(v[2])
    datas = {}
    for k , v in data.items():
        if v[0]==0:
            continue
        datas[k]=v



    return render_template("index.html", data= datas , real = usd(real))


@app.route("/history")
@login_required
def history():
    """Show history of transactions"""
    rows = db.execute("SELECT * FROM history WHERE userid = :ide", ide = session["user_id"] )
    data = []


    for row in range(len(rows)):
        data.append(( rows[row]["symbol"] ,int(rows[row]["shares"]),usd(rows[row]["price"]),rows[row]["transacted"]) )

   # for d in range(len(data)):
    #    data[d][2]=usd(data[d][2])

    return render_template("history.html", data= data )




@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
    """Sell shares of stock"""
    if request.method == "GET":
        sellin= db.execute("SELECT * FROM history WHERE userid = :ide", ide = session["user_id"] )

        data = {}
        for row in range(len(sellin)):
            if sellin[row]["symbol"] in data.keys():
                data[sellin[row]["symbol"]][0]=data[sellin[row]["symbol"]][0]+ sellin[row]["shares"]
            else:
                sell = lookup(sellin[row]["symbol"])
                data[sellin[row]["symbol"]] = [int(sellin[row]["shares"]),sell["price"],0.0 ]
        for k , v in data.items():
            v[2]= v[0]*v[1]

        return render_template("sell.html", data = data)
    elif  request.method == "POST":
        if not request.form.get("symbol")  :
            return  apology("You must provide the stock symbol",400)

        if not request.form.get("shares")  :
            return  apology("You must provide the number of stocks",400)

        if  int(request.form.get("shares"))<0  :
            return  apology("You must provide a suitable number number of stocks",400)
        #if not sell:
       #      return apology("Invalid symbol",403)
        sellin= db.execute("SELECT * FROM history WHERE userid = :ide", ide = session["user_id"] )

        data = {}
        for row in range(len(sellin)):
            if sellin[row]["symbol"] in data.keys():
                data[sellin[row]["symbol"]][0]=data[sellin[row]["symbol"]][0]+ sellin[row]["shares"]
            else:
                sell = lookup(sellin[row]["symbol"])
                data[sellin[row]["symbol"]] = [int(sellin[row]["shares"]),sell["price"],0.0 ]
        for k , v in data.items():
            v[2]= v[0]*v[1]
        if request.form.get("symbol") not  in data.keys():
            return apology("you don't own  this stock",400)

        if  int(request.form.get("shares")) > data[request.form.get("symbol")][0]:
            return  apology("You must provide a suitable number of stocks",400)
        #for k , v in data.items():
         #   v[1]=usd(v[1])
         #  v[2]=usd(v[2])

        minus = int(request.form.get("shares") )* sell["price"]

        db.execute("UPDATE users SET cash = cash + :minus WHERE id = :idi", minus = minus , idi = session["user_id"] )

        db.execute("INSERT INTO history (userid , symbol , shares , price) VALUES (:us , :sy , :sh , :pr)", us = session["user_id"],sy = request.form.get("symbol") , sh = -1 *int(request.form.get("shares")) , pr = sell["price"]   )

        return redirect("/")
    else :
        return render_template("sell.html")



def errorhandler(e):
    """Handle error"""
    return apology(e.name, e.code)


# listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
