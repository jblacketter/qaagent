package main

import (
	"net/http"

	"github.com/gin-gonic/gin"
	"github.com/labstack/echo/v4"
)

func main() {
	http.HandleFunc("GET /health", healthHandler)

	mux := http.NewServeMux()
	mux.HandleFunc("/metrics", metricsHandler)

	r := gin.Default()
	api := r.Group("/api", AuthMiddleware())
	api.GET("/items/:id", getItem)
	api.POST("/items", createItem)
	api.GET("/files/*path", getFile)

	e := echo.New()
	v1 := e.Group("/v1", jwtMiddleware())
	v1.PUT("/users/:id", updateUser)
	v1.DELETE("/users/:id", deleteUser)
}

func healthHandler(_ http.ResponseWriter, _ *http.Request) {}
func metricsHandler(_ http.ResponseWriter, _ *http.Request) {}
func getItem(_ any) {}
func createItem(_ any) {}
func getFile(_ any) {}
func updateUser(_ any) {}
func deleteUser(_ any) {}
func AuthMiddleware() any { return nil }
func jwtMiddleware() any { return nil }
