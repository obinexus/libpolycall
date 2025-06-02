package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"net/http"
)

func testPost() {
	url := "http://localhost:8080/books"
	book := map[string]string{"title": "Test Book", "author": "Test Author"}
	postData, _ := json.Marshal(book)

	req, _ := http.NewRequest("POST", url, bytes.NewBuffer(postData))
	req.Header.Set("Content-Type", "application/json")

	client := &http.Client{}
	resp, err := client.Do(req)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	defer resp.Body.Close()

	body, _ := ioutil.ReadAll(resp.Body)
	var createdBook map[string]interface{}
	json.Unmarshal(body, &createdBook)
	fmt.Println("Created book:", createdBook)

	testGet()
}

func testGet() {
	url := "http://localhost:8080/books"

	resp, err := http.Get(url)
	if err != nil {
		fmt.Println("Error:", err)
		return
	}
	defer resp.Body.Close()

	body, _ := ioutil.ReadAll(resp.Body)
	var books []map[string]interface{}
	json.Unmarshal(body, &books)
	fmt.Println("Books list:", books)
}

func main() {
	testPost()
}