# Code Examples

## Database Architecture
```sql
-- Example: E-commerce Database Schema Design

-- Users table with proper indexing and security
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- bcrypt hashed
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    deleted_at TIMESTAMP WITH TIME ZONE NULL -- Soft delete
);

-- Indexes for performance
CREATE INDEX idx_users_email ON users(email) WHERE deleted_at IS NULL;
CREATE INDEX idx_users_created_at ON users(created_at);

-- Products table with proper normalization
CREATE TABLE products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    price DECIMAL(10,2) NOT NULL CHECK (price >= 0),
    category_id UUID REFERENCES categories(id),
    inventory_count INTEGER DEFAULT 0 CHECK (inventory_count >= 0),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    is_active BOOLEAN DEFAULT true
);

-- Optimized indexes for common queries
CREATE INDEX idx_products_category ON products(category_id) WHERE is_active = true;
CREATE INDEX idx_products_price ON products(price) WHERE is_active = true;
CREATE INDEX idx_products_name_search ON products USING gin(to_tsvector('english', name));
```

## API Design with ESM, Rate Limiting, and Observability
```javascript
import express from 'express';
import helmet from 'helmet';
import rateLimit from 'express-rate-limit';
import { authenticate } from './middleware/auth.js';

const app = express();

// Security middleware
app.use(helmet({
  contentSecurityPolicy: {
    directives: {
      defaultSrc: ["'self'"],
      styleSrc: ["'self'", "'unsafe-inline'"],
      scriptSrc: ["'self'"],
      imgSrc: ["'self'", "data:", "https:"],
    },
  },
}));

// Rate limiting applied to the API router, not app-level
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 100,
  message: 'Too many requests from this IP, please try again later.',
  standardHeaders: true,
  legacyHeaders: false,
});

const apiRouter = express.Router();
apiRouter.use(apiLimiter);

// Routes defined on the router so the limiter actually applies
apiRouter.get('/users/:id', authenticate, async (req, res, next) => {
  const started = Date.now();
  try {
    const user = await req.app.locals.userService.findById(req.params.id);
    if (!user) {
      return res.status(404).json({
        error: 'User not found',
        code: 'USER_NOT_FOUND',
      });
    }
    req.app.locals.metrics.increment('user.fetch.success');
    res.json({ data: user, meta: { timestamp: new Date().toISOString() } });
  } catch (error) {
    req.app.locals.metrics.increment('user.fetch.failure');
    next(error);
  } finally {
    req.app.locals.metrics.histogram('user.fetch.latency_ms', Date.now() - started);
  }
});

app.use('/api', apiRouter);
```
