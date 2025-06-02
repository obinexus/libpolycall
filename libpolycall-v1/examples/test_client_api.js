// test_client.js
const http = require('http');

// Helper function to make HTTP requests
function makeRequest(method, path, data = null) {
    return new Promise((resolve, reject) => {
        const requestOptions = {
            hostname: 'localhost',
            port: 8084,
            path,
            method,
            headers: {
                'Content-Type': 'application/json'
            }
        };

        const req = http.request(requestOptions, (res) => {
            let data = '';
            
            res.on('data', chunk => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const result = JSON.parse(data);
                    resolve(result);
                } catch (error) {
                    reject(error);
                }
            });
        });

        req.on('error', reject);

        if (data) {
            req.write(JSON.stringify(data));
        }
        
        req.end();
    });
}

// Test functions
async function testCreateBook() {
    console.log('\nTesting POST /books');
    try {
        const bookData = {
            title: 'Test Book',
            author: 'Test Author'
        };
        const result = await makeRequest('POST', '/books', bookData);
        console.log('Created book:', result);
        return result;
    } catch (error) {
        console.error('Failed to create book:', error.message);
        throw error;
    }
}

async function testGetBooks() {
    console.log('\nTesting GET /books');
    try {
        const result = await makeRequest('GET', '/books');
        console.log('Books list:', result);
        return result;
    } catch (error) {
        console.error('Failed to get books:', error.message);
        throw error;
    }
}

// Run tests
async function runTests() {
    try {
        // First create a book
        await testCreateBook();
        
        // Then get all books
        await testGetBooks();
        
    } catch (error) {
        console.error('Test suite failed:', error.message);
    }
}

// Run the tests
runTests();