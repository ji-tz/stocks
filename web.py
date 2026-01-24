from flask import Flask, render_template_string

app = Flask(__name__)

@app.route('/')
def index():
    return render_template_string('''
    <html>
    <head><title>量化回测平台</title></head>
    <body>
        <h1>欢迎使用量化回测平台</h1>
        <p>本平台基于Backtrader和AKShare，支持A股回测。</p>
    </body>
    </html>
    ''')

if __name__ == '__main__':
    app.run(debug=True)
