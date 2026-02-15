Rails.application.routes.draw do
  namespace :api do
    resources :users, only: [:index, :show, :create, :update, :destroy]
    get "/health", to: "health#show"
    match "/status", to: "status#show", via: [:get, :post]
  end
end
