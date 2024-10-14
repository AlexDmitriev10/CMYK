import os
from flask import Flask, render_template, request
from PIL import Image
import numpy as np
from werkzeug.exceptions import RequestEntityTooLarge

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 32 * 1024 * 1024



def rgb_to_cmyk(r, g, b):
    if (r == 0) and (g == 0) and (b == 0):
        return 0, 0, 0, 100
    r_prime = r / 255.0
    g_prime = g / 255.0
    b_prime = b / 255.0
    k = 1 - max(r_prime, g_prime, b_prime)
    if k == 1:
        return 0, 0, 0, 100
    c = (1 - r_prime - k) / (1 - k)
    m = (1 - g_prime - k) / (1 - k)
    y = (1 - b_prime - k) / (1 - k)
    return round(c * 100), round(m * 100), round(y * 100), round(k * 100)


def load_image(image_path):
    return Image.open(image_path)


def calculate_toner_usage(image):
    image = image.convert('RGB')
    pixels = np.array(image)
    total_pixels = pixels.shape[0] * pixels.shape[1]

    c_total, m_total, y_total, k_total = 0, 0, 0, 0

    for pixel in pixels.reshape(-1, 3):
        c, m, y, k = rgb_to_cmyk(*pixel)
        c_total += c
        m_total += m
        y_total += y
        k_total += k

    c_usage = c_total / total_pixels / 100
    m_usage = m_total / total_pixels / 100
    y_usage = y_total / total_pixels / 100
    k_usage = k_total / total_pixels / 100

    return c_usage, m_usage, y_usage, k_usage


def calculate_print_cost(image_path, c_cost, m_cost, y_cost, k_cost):
    image = load_image(image_path)
    c_usage, m_usage, y_usage, k_usage = calculate_toner_usage(image)

    total_cost = (c_usage * c_cost) + (m_usage * m_cost) + (y_usage * y_cost) + (k_usage * k_cost)

    return total_cost, c_usage, m_usage, y_usage, k_usage


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':

        if 'image' not in request.files:
            return 'Не выбрано изображение!'
        file = request.files['image']
        if file.filename == '':
            return 'Файл не выбран!'
        if file:
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
            file.save(filepath)
            try:
                c_cost = float(request.form['cyan'])
                m_cost = float(request.form['magenta'])
                y_cost = float(request.form['yellow'])
                k_cost = float(request.form['black'])

                total_cost, c_usage, m_usage, y_usage, k_usage = calculate_print_cost(filepath, c_cost, m_cost, y_cost,
                                                                                      k_cost)
                return render_template('result.html', total_cost=total_cost, c_usage=c_usage, m_usage=m_usage,
                                       y_usage=y_usage, k_usage=k_usage)

            except ValueError:
                return 'Некорректный ввод стоимости картриджей.'

    return render_template('index.html')


@app.errorhandler(RequestEntityTooLarge)
def handle_large_file(e):
    return "Размер файла слишком велик. Загрузите файл размером меньше 32MB.", 413


if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'])

    app.run(debug=True, host='0.0.0.0', port=5001)
