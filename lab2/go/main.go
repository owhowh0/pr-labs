package main

import (
	"coffeeshop/server"
	"flag"
	"log"
)

func main() {
	port := flag.Int("port", 8080, "Port to listen on")
	flag.Parse()

	server := server.NewServer(*port)
	if err := server.Start(); err != nil {
		log.Fatalf("Server error: %v", err)
	}
}
