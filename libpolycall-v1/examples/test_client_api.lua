local http = require("socket.http")
local ltn12 = require("ltn12")
local json = require("cjson")

-- Helper function to make HTTP requests
local function makeRequest(method, path, data)
    local response_body = {}
    local url = "http://localhost:8080" .. path
    
    local headers = {
        ["Content-Type"] = "application/json"
    }
    
    local request_body = data and json.encode(data) or ""
    
    headers["Content-Length"] = #request_body
    
    local res, code, response_headers = http.request{
        url = url,
        method = method,
        headers = headers,
        source = ltn12.source.string(request_body),
        sink = ltn12.sink.table(response_body)
    }
    
    if code ~= 200 then
        error("HTTP request failed with code: " .. tostring(code))
    end
    
    local response_data = table.concat(response_body)
    return json.decode(response_data)
end

-- Test functions
local function testCreateBook()
    print("\nTesting POST /books")
    local ok, result = pcall(function()
        local bookData = {
            title = "Test Book",
            author = "Test Author"
        }
        local response = makeRequest("POST", "/books", bookData)
        print("Created book:", json.encode(response))
        return response
    end)
    
    if not ok then
        print("Failed to create book:", result)
        error(result)
    end
    return result
end

local function testGetBooks()
    print("\nTesting GET /books")
    local ok, result = pcall(function()
        local response = makeRequest("GET", "/books")
        print("Books list:", json.encode(response))
        return response
    end)
    
    if not ok then
        print("Failed to get books:", result)
        error(result)
    end
    return result
end

-- Run tests
local function runTests()
    local ok, err = pcall(function()
        -- First create a book
        testCreateBook()
        
        -- Then get all books
        testGetBooks()
    end)
    
    if not ok then
        print("Test suite failed:", err)
    end
end

-- Run the tests
runTests()