
import {
  ShoppingBag,
  Clapperboard,
  MessageCircle,
  House,
  WalletCards,
  ChartNoAxesCombined,
  Truck,
} from 'lucide-react';

export const services = {
  ecommerce: {
    number: '01',
    title: 'E-commerce',
    eyebrow: 'SHOPPING, REIMAGINED',
    headline: 'Discover more. Shop with Univa.',
    description:
      'Explore a connected shopping experience designed to bring products, shops, and customers closer together.',
    icon: ShoppingBag,
    accent: '#315de8',
    tint: '#edf2ff',
    benefits: [
      {
        title: 'Discover products',
        description:
          'Explore products and discover items that match your interests.',
      },
      {
        title: 'Explore shops',
        description:
          'Find businesses and browse their products in one connected experience.',
      },
      {
        title: 'A connected journey',
        description:
          'Discover how shopping can connect with other services across Univa.',
      },
    ],
    cta: 'Explore the Univa ecosystem',
    ctaHref: '/about',
  },

  social: {
    number: '02',
    title: 'Social',
    eyebrow: 'CONNECT THROUGH CONTENT',
    headline: 'Discover stories. Find your people.',
    description:
      'A social experience designed around discovering content, following creators, sharing ideas, and building communities.',
    icon: Clapperboard,
    accent: '#7852d6',
    tint: '#f2edff',
    benefits: [
      {
        title: 'Discover content',
        description:
          'Explore content and ideas from across your areas of interest.',
      },
      {
        title: 'Creator discovery',
        description:
          'Find creators and perspectives that inspire you.',
      },
      {
        title: 'Build community',
        description:
          'Connect around shared interests and conversations.',
      },
    ],
    cta: 'Discover Univa',
    ctaHref: '/about',
  },

  chat: {
    number: '03',
    title: 'Chat',
    eyebrow: 'CONVERSATIONS THAT CONNECT',
    headline: 'Keep every conversation closer.',
    description:
      'Discover Univa Chat, designed to bring conversations, group communication, and everyday connections into one experience.',
    icon: MessageCircle,
    accent: '#168b87',
    tint: '#e5f8f6',
    benefits: [
      {
        title: 'Personal conversations',
        description:
          'A dedicated space for one-to-one communication.',
      },
      {
        title: 'Group communication',
        description:
          'Bring people together around shared plans and interests.',
      },
      {
        title: 'Connected experiences',
        description:
          'A communication experience that belongs to the wider Univa ecosystem.',
      },
    ],
    cta: 'Explore Univa',
    ctaHref: '/about',
  },

  'real-estate': {
    number: '04',
    title: 'Real Estate',
    eyebrow: 'FIND YOUR NEXT OPPORTUNITY',
    headline: 'Find spaces for what comes next.',
    description:
      'Explore a property experience designed to help people discover homes, investigate locations, and connect with real estate opportunities.',
    icon: House,
    accent: '#cb772d',
    tint: '#fff2e6',
    benefits: [
      {
        title: 'Discover properties',
        description:
          'Explore property opportunities for different needs and preferences.',
      },
      {
        title: 'Explore locations',
        description:
          'Learn about locations and the possibilities they offer.',
      },
      {
        title: 'Make informed choices',
        description:
          'Organize your property search around the details that matter to you.',
      },
    ],
    cta: 'Explore the Univa ecosystem',
    ctaHref: '/about',
  },

  banking: {
    number: '05',
    title: 'Banking',
    eyebrow: 'FINANCIAL SERVICES, CONNECTED',
    headline: 'A more connected financial experience.',
    description:
      'Discover Univa’s vision for accessible financial services within a broader digital ecosystem.',
    icon: WalletCards,
    accent: '#21875a',
    tint: '#e7f7ed',
    benefits: [
      {
        title: 'Financial services',
        description:
          'Discover financial tools and services available through the platform.',
      },
      {
        title: 'A connected experience',
        description:
          'Explore how financial services can complement everyday digital activities.',
      },
      {
        title: 'Security and trust',
        description:
          'Understand the importance of secure, responsible financial experiences.',
      },
    ],
    cta: 'Learn about Univa',
    ctaHref: '/about',
  },

  investments: {
    number: '06',
    title: 'Investments',
    eyebrow: 'OPPORTUNITIES WITH PURPOSE',
    headline: 'Explore opportunities. Think long term.',
    description:
      'Discover the investment component of the Univa ecosystem, built around exploring opportunities and making informed decisions.',
    icon: ChartNoAxesCombined,
    accent: '#247b67',
    tint: '#e6f5ef',
    benefits: [
      {
        title: 'Explore opportunities',
        description:
          'Learn about investment opportunities presented through the platform.',
      },
      {
        title: 'Understand the details',
        description:
          'Review relevant information, risks, and terms before making decisions.',
      },
      {
        title: 'A responsible approach',
        description:
          'Build financial decisions around informed evaluation rather than promises of returns.',
      },
    ],
    cta: 'Contact our team',
    ctaHref: '/contact',
  },

  transport: {
    number: '07',
    title: 'Transport & Logistics',
    eyebrow: 'KEEP PEOPLE AND GOODS MOVING',
    headline: 'Move people. Deliver possibilities.',
    description:
      'Explore a connected mobility and logistics experience for rides, deliveries, courier services, and moving goods.',
    icon: Truck,
    accent: '#c34f87',
    tint: '#ffedf5',
    benefits: [
      {
        title: 'Mobility',
        description:
          'Discover transport services designed around getting people where they need to go.',
      },
      {
        title: 'Deliveries',
        description:
          'Explore delivery and courier experiences for everyday needs.',
      },
      {
        title: 'Logistics',
        description:
          'Connect goods, delivery needs, and logistics opportunities in one ecosystem.',
      },
    ],
    cta: 'Explore the Univa ecosystem',
    ctaHref: '/about',
  },
};
