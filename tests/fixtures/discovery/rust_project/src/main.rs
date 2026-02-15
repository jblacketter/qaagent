use actix_web::{get, post, web, HttpResponse, Responder};
use axum::routing::{get, post};
use axum::Router;
use tower_http::auth::RequireAuthorizationLayer;

#[get("/health")]
async fn health() -> impl Responder {
    HttpResponse::Ok()
}

#[post("/login")]
async fn login() -> impl Responder {
    HttpResponse::Created()
}

fn actix_routes() {
    let _ = web::scope("/api")
        .route("/items/{id}", web::get().to(get_item))
        .route("/items", web::post().to(create_item));
}

fn axum_routes() {
    let _app = Router::new()
        .route("/users/:id", get(get_user))
        .route("/users", post(create_user))
        .route("/admin", get(authenticated_admin).post(authenticated_admin_post))
        .layer(RequireAuthorizationLayer::bearer("token"));
}

async fn get_item() {}
async fn create_item() {}
async fn get_user() {}
async fn create_user() {}
async fn authenticated_admin() {}
async fn authenticated_admin_post() {}
