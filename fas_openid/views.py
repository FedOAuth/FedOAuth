@app.route('/')
def view_main():
    return render_template('index.html')
