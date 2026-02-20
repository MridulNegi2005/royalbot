from flask import Flask, redirect, url_for, request,render_template
app = Flask(__name__)
import time
import os
from dotenv import load_dotenv
load_dotenv()
import psycopg2
con = psycopg2.connect(os.getenv('HEROKU_POSTGRES_URI'), sslmode='require')
query = con.cursor()
@app.route('/')
def hello_world():
    time2=1686843000
    msg_id= request.args['msg']

    try:
        sql='SELECT * FROM gconfig where message=%s'
        query.execute(sql,(msg_id,))
        myresult = query.fetchall()
        print(myresult)
        print("UPAR DEKH!")
        time2 = myresult[0][0]
    except:
        pass
    return render_template('index.html',sec=time2)

if __name__ == '__main__':
    app.run(host="0.0.0.0",debug=True,)