from flask import Flask, redirect, url_for, request,render_template
app = Flask(__name__)
import time
import psycopg2
con = psycopg2.connect('postgres://balxuonbzytruy:2be081d80c21d0869d500f997e19ff385ad5278d020402608fc23ac1f8d71bc6@ec2-52-73-184-24.compute-1.amazonaws.com:5432/des0u9rjq76pq', sslmode='require')
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