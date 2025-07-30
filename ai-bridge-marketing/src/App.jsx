import { useState, useEffect } from 'react'
import { Button } from '@/components/ui/button.jsx'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card.jsx'
import { Input } from '@/components/ui/input.jsx'
import { Label } from '@/components/ui/label.jsx'
import { Badge } from '@/components/ui/badge.jsx'
import { 
  Database, 
  Target, 
  Users, 
  BarChart3, 
  CheckCircle, 
  ArrowRight, 
  Star,
  Shield,
  Zap,
  Globe,
  Brain,
  Eye,
  MessageSquare,
  Award,
  Clock,
  TrendingUp,
  Play,
  ChevronRight,
  Menu,
  X
} from 'lucide-react'
import './App.css'

function App() {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const [activeTestimonial, setActiveTestimonial] = useState(0)

  // Auto-rotate testimonials
  useEffect(() => {
    const interval = setInterval(() => {
      setActiveTestimonial((prev) => (prev + 1) % testimonials.length)
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="min-h-screen bg-background">
      <Header isMenuOpen={isMenuOpen} setIsMenuOpen={setIsMenuOpen} />
      <HeroSection />
      <ServicesSection />
      <FeaturesSection />
      <TestimonialsSection activeTestimonial={activeTestimonial} setActiveTestimonial={setActiveTestimonial} />
      <StatsSection />
      <PricingSection />
      <CTASection />
      <Footer />
    </div>
  )
}

// Header Component
function Header({ isMenuOpen, setIsMenuOpen }) {
  return (
    <header className="sticky top-0 z-50 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex h-16 items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-primary rounded-lg flex items-center justify-center">
              <Database className="w-6 h-6 text-primary-foreground" />
            </div>
            <span className="text-2xl font-bold">AI Bridge</span>
          </div>
          
          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center space-x-8">
            <a href="#services" className="text-foreground/80 hover:text-foreground transition-colors">Services</a>
            <a href="#features" className="text-foreground/80 hover:text-foreground transition-colors">Features</a>
            <a href="#pricing" className="text-foreground/80 hover:text-foreground transition-colors">Pricing</a>
            <a href="#about" className="text-foreground/80 hover:text-foreground transition-colors">About</a>
            <Button variant="outline" asChild>
              <a href="http://localhost:5173" target="_blank" rel="noopener noreferrer">
                Platform Login
              </a>
            </Button>
            <Button asChild>
              <a href="#contact">Get Started</a>
            </Button>
          </nav>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            {isMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>

        {/* Mobile Navigation */}
        {isMenuOpen && (
          <div className="md:hidden py-4 border-t">
            <nav className="flex flex-col space-y-4">
              <a href="#services" className="text-foreground/80 hover:text-foreground transition-colors">Services</a>
              <a href="#features" className="text-foreground/80 hover:text-foreground transition-colors">Features</a>
              <a href="#pricing" className="text-foreground/80 hover:text-foreground transition-colors">Pricing</a>
              <a href="#about" className="text-foreground/80 hover:text-foreground transition-colors">About</a>
              <Button variant="outline" className="w-full" asChild>
                <a href="http://localhost:5173" target="_blank" rel="noopener noreferrer">
                  Platform Login
                </a>
              </Button>
              <Button className="w-full" asChild>
                <a href="#contact">Get Started</a>
              </Button>
            </nav>
          </div>
        )}
      </div>
    </header>
  )
}

// Hero Section
function HeroSection() {
  return (
    <section className="relative py-20 lg:py-32 overflow-hidden">
      <div className="absolute inset-0 bg-gradient-to-br from-primary/5 to-secondary/5" />
      <div className="container mx-auto px-4 sm:px-6 lg:px-8 relative">
        <div className="max-w-4xl mx-auto text-center">
          <Badge className="mb-6" variant="secondary">
            <Star className="w-4 h-4 mr-2" />
            Arabic Data Specialization
          </Badge>
          <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold tracking-tight mb-6">
            Professional 
            <span className="text-primary"> Data Labeling</span>
            <br />
            for AI Excellence
          </h1>
          <p className="text-xl text-muted-foreground mb-8 max-w-2xl mx-auto">
            Specialized Arabic data annotation services backed by AI consulting expertise. 
            We combine technical precision with strategic guidance to help your AI projects succeed.
          </p>
          <div className="flex flex-col sm:flex-row gap-4 justify-center">
            <Button size="lg" className="text-lg px-8" asChild>
              <a href="#contact">
                Start Your Project
                <ArrowRight className="w-5 h-5 ml-2" />
              </a>
            </Button>
            <Button size="lg" variant="outline" className="text-lg px-8">
              <Play className="w-5 h-5 mr-2" />
              Watch Demo
            </Button>
          </div>
        </div>
      </div>
    </section>
  )
}

// Services Section
function ServicesSection() {
  const services = [
    {
      icon: Eye,
      title: "Computer Vision",
      description: "Object detection, image classification, semantic segmentation, and facial recognition labeling.",
      features: ["Bounding boxes", "Polygons", "Keypoints", "3D annotations"]
    },
    {
      icon: MessageSquare,
      title: "Natural Language Processing",
      description: "Text classification, named entity recognition, sentiment analysis, and language understanding.",
      features: ["Entity tagging", "Intent classification", "Sentiment scoring", "Text summarization"]
    },
    {
      icon: Brain,
      title: "Machine Learning",
      description: "Custom annotation workflows for specialized ML models and reinforcement learning applications.",
      features: ["RLHF training", "Model fine-tuning", "Custom workflows", "Quality assurance"]
    },
    {
      icon: Globe,
      title: "Medical & Healthcare",
      description: "HIPAA-compliant medical image annotation and healthcare data labeling services.",
      features: ["Medical imaging", "Clinical data", "HIPAA compliance", "Expert annotators"]
    }
  ]

  return (
    <section id="services" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Our Data Labeling Services</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            Comprehensive annotation services across all major AI domains with industry-leading accuracy and speed.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
          {services.map((service, index) => (
            <Card key={index} className="group hover:shadow-lg transition-all duration-300 hover:-translate-y-1">
              <CardHeader>
                <div className="w-12 h-12 bg-primary/10 rounded-lg flex items-center justify-center mb-4 group-hover:bg-primary/20 transition-colors">
                  <service.icon className="w-6 h-6 text-primary" />
                </div>
                <CardTitle className="text-xl">{service.title}</CardTitle>
                <CardDescription className="text-base">{service.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  {service.features.map((feature, idx) => (
                    <div key={idx} className="flex items-center text-sm text-muted-foreground">
                      <CheckCircle className="w-4 h-4 text-primary mr-2 flex-shrink-0" />
                      {feature}
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

// Features Section
function FeaturesSection() {
  const features = [
    {
      icon: Shield,
      title: "Enterprise Security",
      description: "SOC 2 compliant with end-to-end encryption and secure data handling."
    },
    {
      icon: Zap,
      title: "Efficient Workflows",
      description: "Streamlined processes designed for quality and consistency."
    },
    {
      icon: Award,
      title: "Quality Focused",
      description: "Multi-layer quality assurance with expert review processes."
    },
    {
      icon: Users,
      title: "Expert Team",
      description: "Domain experts and certified annotators for specialized projects."
    },
    {
      icon: BarChart3,
      title: "Real-time Analytics",
      description: "Track progress and quality metrics with detailed reporting."
    },
    {
      icon: Globe,
      title: "Arabic Specialization",
      description: "Expert knowledge in Arabic language data annotation and cultural context."
    }
  ]

  return (
    <section id="features" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Why Choose AI Bridge?</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            We combine cutting-edge technology with human expertise to deliver the highest quality labeled data.
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
          {features.map((feature, index) => (
            <div key={index} className="text-center group">
              <div className="w-16 h-16 bg-primary/10 rounded-full flex items-center justify-center mx-auto mb-6 group-hover:bg-primary/20 transition-colors">
                <feature.icon className="w-8 h-8 text-primary" />
              </div>
              <h3 className="text-xl font-semibold mb-3">{feature.title}</h3>
              <p className="text-muted-foreground">{feature.description}</p>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Testimonials Data
const testimonials = [
  {
    name: "Sarah Chen",
    role: "ML Engineer at TechCorp",
    content: "AI Bridge transformed our computer vision project. Their annotation quality is exceptional and delivery was 3x faster than our previous provider.",
    rating: 5
  },
  {
    name: "Marcus Rodriguez",
    role: "Data Scientist at HealthAI",
    content: "The medical image annotations were perfect. HIPAA compliance and expert knowledge made all the difference for our healthcare AI model.",
    rating: 5
  },
  {
    name: "Emily Watson",
    role: "Research Director at AutoDrive",
    content: "Outstanding service for our autonomous vehicle project. The precision of their 3D annotations exceeded our expectations.",
    rating: 5
  }
]

// Testimonials Section
function TestimonialsSection({ activeTestimonial, setActiveTestimonial }) {
  return (
    <section className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">What Our Clients Say</h2>
          <p className="text-xl text-muted-foreground">
            Trusted by leading AI companies worldwide
          </p>
        </div>
        
        <div className="max-w-4xl mx-auto">
          <Card className="p-8">
            <CardContent className="text-center">
              <div className="flex justify-center mb-4">
                {[...Array(testimonials[activeTestimonial].rating)].map((_, i) => (
                  <Star key={i} className="w-5 h-5 text-yellow-400 fill-current" />
                ))}
              </div>
              <blockquote className="text-xl italic mb-6">
                "{testimonials[activeTestimonial].content}"
              </blockquote>
              <div>
                <div className="font-semibold">{testimonials[activeTestimonial].name}</div>
                <div className="text-muted-foreground">{testimonials[activeTestimonial].role}</div>
              </div>
            </CardContent>
          </Card>
          
          <div className="flex justify-center mt-8 space-x-2">
            {testimonials.map((_, index) => (
              <button
                key={index}
                className={`w-3 h-3 rounded-full transition-colors ${
                  index === activeTestimonial ? 'bg-primary' : 'bg-muted'
                }`}
                onClick={() => setActiveTestimonial(index)}
              />
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

// Stats Section
function StatsSection() {
  const stats = [
    { number: "Arabic", label: "Language Specialization" },
    { number: "Secure", label: "GDPR Compliant" },
    { number: "Expert", label: "Quality Assurance" },
    { number: "Custom", label: "Project Timelines" }
  ]

  return (
    <section className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-12">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Our Commitment to Quality</h2>
          <p className="text-xl text-muted-foreground max-w-2xl mx-auto">
            We focus on delivering exceptional results through specialized expertise and proven methodologies.
          </p>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-8">
          {stats.map((stat, index) => (
            <div key={index} className="text-center">
              <div className="text-2xl lg:text-3xl font-bold text-primary mb-2">{stat.number}</div>
              <div className="text-muted-foreground">{stat.label}</div>
            </div>
          ))}
        </div>
      </div>
    </section>
  )
}

// Pricing Section
function PricingSection() {
  const plans = [
    {
      name: "Starter",
      price: "$0.10",
      unit: "per annotation",
      description: "Perfect for small projects and prototypes",
      features: [
        "Basic image classification",
        "Text annotation",
        "Standard quality assurance",
        "Email support",
        "Project-based timeline"
      ]
    },
    {
      name: "Professional",
      price: "$0.25",
      unit: "per annotation",
      description: "Ideal for production AI models",
      features: [
        "All Starter features",
        "Object detection & segmentation",
        "Multi-layer QA process",
        "Priority support",
        "Expedited delivery",
        "Custom workflows"
      ],
      popular: true
    },
    {
      name: "Enterprise",
      price: "Custom",
      unit: "pricing",
      description: "For large-scale AI initiatives",
      features: [
        "All Professional features",
        "Dedicated project manager",
        "HIPAA compliance",
        "24/7 support",
        "Priority delivery",
        "On-premise deployment"
      ]
    }
  ]

  return (
    <section id="pricing" className="py-20 bg-muted/30">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center mb-16">
          <h2 className="text-3xl lg:text-4xl font-bold mb-4">Simple, Transparent Pricing</h2>
          <p className="text-xl text-muted-foreground">
            Choose the plan that fits your project needs
          </p>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-6xl mx-auto">
          {plans.map((plan, index) => (
            <Card key={index} className={`relative ${plan.popular ? 'border-primary shadow-lg scale-105' : ''}`}>
              {plan.popular && (
                <Badge className="absolute -top-3 left-1/2 transform -translate-x-1/2">
                  Most Popular
                </Badge>
              )}
              <CardHeader className="text-center">
                <CardTitle className="text-2xl">{plan.name}</CardTitle>
                <div className="mt-4">
                  <span className="text-4xl font-bold">{plan.price}</span>
                  <span className="text-muted-foreground ml-2">{plan.unit}</span>
                </div>
                <CardDescription className="mt-2">{plan.description}</CardDescription>
              </CardHeader>
              <CardContent>
                <ul className="space-y-3">
                  {plan.features.map((feature, idx) => (
                    <li key={idx} className="flex items-center">
                      <CheckCircle className="w-5 h-5 text-primary mr-3 flex-shrink-0" />
                      <span className="text-sm">{feature}</span>
                    </li>
                  ))}
                </ul>
                <Button className="w-full mt-6" variant={plan.popular ? "default" : "outline"}>
                  Get Started
                  <ChevronRight className="w-4 h-4 ml-2" />
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    </section>
  )
}

// CTA Section
function CTASection() {
  return (
    <section id="contact" className="py-20">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <Card className="bg-gradient-to-r from-primary to-primary/80 text-primary-foreground">
          <CardContent className="p-12 text-center">
            <h2 className="text-3xl lg:text-4xl font-bold mb-4">
              Ready to Scale Your AI Project?
            </h2>
            <p className="text-xl mb-8 opacity-90 max-w-2xl mx-auto">
              Partner with AI Bridge for professional data labeling services backed by 
              consulting expertise and Arabic language specialization.
            </p>
            <div className="flex flex-col sm:flex-row gap-4 justify-center">
              <Button size="lg" variant="secondary" className="text-lg px-8">
                Schedule Consultation
                <Clock className="w-5 h-5 ml-2" />
              </Button>
              <Button size="lg" variant="outline" className="text-lg px-8 border-primary-foreground text-primary-foreground hover:bg-primary-foreground hover:text-primary">
                <a href="http://localhost:5173" target="_blank" rel="noopener noreferrer" className="flex items-center">
                  Try Platform Demo
                  <TrendingUp className="w-5 h-5 ml-2" />
                </a>
              </Button>
            </div>
          </CardContent>
        </Card>
      </div>
    </section>
  )
}

// Footer
function Footer() {
  return (
    <footer className="bg-muted/30 py-12">
      <div className="container mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
          <div>
            <div className="flex items-center space-x-2 mb-4">
              <div className="w-8 h-8 bg-primary rounded-lg flex items-center justify-center">
                <Database className="w-5 h-5 text-primary-foreground" />
              </div>
              <span className="text-xl font-bold">AI Bridge</span>
            </div>
            <p className="text-muted-foreground">
              Professional data labeling services for AI excellence.
            </p>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Services</h3>
            <ul className="space-y-2 text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">Computer Vision</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">NLP</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Machine Learning</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Medical AI</a></li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Company</h3>
            <ul className="space-y-2 text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">About Us</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Careers</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Blog</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Contact</a></li>
            </ul>
          </div>
          
          <div>
            <h3 className="font-semibold mb-4">Support</h3>
            <ul className="space-y-2 text-muted-foreground">
              <li><a href="#" className="hover:text-foreground transition-colors">Documentation</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">API Reference</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Help Center</a></li>
              <li><a href="#" className="hover:text-foreground transition-colors">Status</a></li>
            </ul>
          </div>
        </div>
        
        <div className="border-t mt-12 pt-8 text-center text-muted-foreground">
          <p>&copy; 2024 AI Bridge. All rights reserved.</p>
        </div>
      </div>
    </footer>
  )
}

export default App

