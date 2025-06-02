import json
import http.client

def test_post():
    conn = http.client.HTTPConnection("localhost", 8084)
    headers = {'Content-type': 'application/json'}
    post_data = json.dumps({'title': 'Test Book', 'author': 'Test Author'})

    conn.request('POST', '/books', post_data, headers)
    response = conn.getresponse()
    data = response.read().decode()
    print('Created book:', json.loads(data))
    
    conn.close()
    test_get()

def test_get():
    conn = http.client.HTTPConnection("localhost", 8084)
    conn.request('GET', '/books')
    response = conn.getresponse()
    data = response.read().decode()
    print('Books list:', json.loads(data))
    
    conn.close()

if __name__ == "__main__":
    test_post()