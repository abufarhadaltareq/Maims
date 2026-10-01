import { BRAND_CONFIG } from '../brand.config.js'

/**
 * EDITABLE BUSINESS DETAILS
 * ------------------------------------------------------------------
 * Everything below is placeholder text. Replace each value with the real
 * details of the business before going live: legal entity name, registered
 * address, company/VAT number, support email and governing law.
 * Have the wording reviewed by a lawyer for your country.
 */
export const LEGAL_DETAILS = {
  legalName: 'Maims',
  tradingName: BRAND_CONFIG.name,
  domain: BRAND_CONFIG.domain,
  supportEmail: BRAND_CONFIG.supportEmail,
  registeredAddress: 'Portugal (insert full registered business address)',
  companyNumber: 'insert company registration number',
  vatNumber: 'insert VAT / tax number (if registered)',
  governingLaw: 'Portugal',
  courts: 'the competent courts of Portugal',
  returnsWindow: '14 days',
  dispatchWindow: '1-3 business days',
  deliveryWindow: '5-12 business days',
  updated: '1 October 2026',
}

const d = LEGAL_DETAILS

export const LEGAL_DOCS = [
  {
    id: 'legal-terms',
    tab: 'Terms & Conditions',
    title: 'Terms & Conditions',
    intro: `These Terms & Conditions govern your use of ${d.domain} and every order placed through it. By browsing the site, creating an account or placing an order you accept them. If you do not agree, please do not use the site.`,
    sections: [
      {
        heading: '1. Who we are',
        body: [
          `${d.tradingName} ("we", "us") trades as ${d.legalName}, ${d.registeredAddress}. Company number: ${d.companyNumber}. VAT number: ${d.vatNumber}.`,
          `Questions about these terms can be sent to ${d.supportEmail}.`,
        ],
      },
      {
        heading: '2. Eligibility and accounts',
        body: [
          'You must be at least 18 years old, or the age of majority where you live, to place an order.',
          'When you create an account you are responsible for keeping your password confidential and for all activity under your account. Tell us immediately if you suspect unauthorised access.',
          'You may not create an account on behalf of someone else, impersonate another person, or use the site to post unlawful content.',
        ],
      },
      {
        heading: '3. Products and availability',
        body: [
          'We sell clothing and fashion accessories. Product photographs, descriptions, weights and measurements are provided for guidance and may vary slightly from the physical item.',
          'Screens display colour differently from real fabric, so shades may vary a little between your screen and the delivered garment.',
          'Products are offered in the sizes and colours listed at the time of ordering. We may correct typos, pricing errors or inaccuracies and will contact you if an order was placed on the basis of a clear error.',
          'Some products are limited in quantity. If an item is unavailable after you order, we will cancel that item and refund it in full.',
        ],
      },
      {
        heading: '4. Prices and currency',
        body: [
          'Prices are shown in the currency you select on the site and exclude delivery and any duties unless stated otherwise.',
          'Where an item is not available in your selected currency, we show a converted estimate for reference only; the final amount charged is the one shown at checkout.',
          'Prices can change without notice, but we never change the price of an order you have already placed.',
          'You are responsible for any customs duties, import taxes or carrier fees charged when your order arrives in your country. We declare the full value on all shipments.',
        ],
      },
      {
        heading: '5. Orders and contract formation',
        body: [
          'Your order is an offer to buy. A contract is formed only when we send the order confirmation email with the dispatch notice.',
          'We may refuse or cancel an order before dispatch, for example where an item is out of stock, the price was listed incorrectly, the delivery address is incomplete, or we reasonably suspect fraud. Any amount already paid is refunded in full.',
          'Where an order has been dispatched and is later cancelled, your right of withdrawal (section 9) applies instead.',
        ],
      },
      {
        heading: '6. Payment',
        body: [
          'We accept the payment methods shown at checkout: card payment, PayPal or bank transfer where available, and cash on delivery in supported regions.',
          'Card payments are handled by our payment provider. We never see or store your full card number; payment details are collected on a secure, provider-hosted page.',
          'Cash on delivery orders are payable in the delivery currency to the courier. If the courier cannot reach you or the order cannot be handed over, it is returned to us and the original delivery fee may not be refundable.',
          'Orders placed through WhatsApp are confirmed by us before they are treated as accepted.',
        ],
      },
      {
        heading: '7. Delivery',
        body: [
          `Orders are dispatched within ${d.dispatchWindow} of confirmation. Estimated delivery is ${d.deliveryWindow} after dispatch, depending on the destination and carrier.`,
          'Delivery is to the address you provide at checkout. Please check it carefully: we are not responsible for parcels lost or delayed because of an incorrect or incomplete address.',
          'If your parcel does not arrive, contact us with your order number and we will trace it with the carrier and, where appropriate, send a replacement or issue a refund.',
          'Risk passes to you on delivery. Please inspect the parcel in the presence of the courier and note any visible damage on the delivery receipt.',
        ],
      },
      {
        heading: '8. Changes and cancellations',
        body: [
          'You can cancel or change an order at any time before it is dispatched, by contacting support.',
          'Once an order has left our warehouse, the order is no longer editable or cancellable, and any return is handled under section 9.',
        ],
      },
      {
        heading: '9. Returns, exchanges and refunds',
        body: [
          `You may withdraw from your purchase within ${d.returnsWindow} of receiving the goods, for any reason, by notifying us at ${d.supportEmail}. A return is not valid until we have confirmed it.`,
          'Items must be returned unused, unworn and unwashed, with all tags and original packaging, in a condition that allows them to be resold.',
          'For hygiene reasons, the following cannot be returned unless faulty: swimwear, lingerie, pierced jewellery, gift cards, and items marked final sale on the product page.',
          'Send returns to the address in your return confirmation. Return shipping costs are yours unless the item is faulty or incorrect. We recommend a tracked service and keeping your proof of postage.',
          'We inspect returns within 5 business days of arrival. Refunds are issued to the original payment method once approved, and your bank may take a further 5-10 business days to show the credit. Original delivery fees are only refunded where the item was faulty or incorrect.',
          'Exchanges for a different size or colour are handled as a return plus a new order, so stock is not reserved for you.',
        ],
      },
      {
        heading: '10. Faulty items and legal guarantees',
        body: [
          'Every item is covered by the statutory guarantee for conformity. If an item is faulty, not as described, or damaged on arrival, tell us within 30 days of delivery with photos.',
          'We will, at your choice, replace the item, repair it where repair is reasonable, or refund the full amount including the original delivery fee.',
          'This guarantee does not cover normal wear, accidental damage, washing or care instructions that were not followed, and changes in how a fabric looks over time.',
        ],
      },
      {
        heading: '11. Discounts and promotional codes',
        body: [
          'Only one promotion code per order unless stated otherwise. Promotions cannot be combined with other offers unless we say otherwise.',
          'Promotions have their own time limits and minimum spend. We may withdraw or change a promotion at any time, but never after you have placed an order using it.',
          'Where a promotion is used in error, we may cancel the affected order and charge the full price.',
        ],
      },
      {
        heading: '12. Acceptable use',
        body: [
          'You may not scrape, crawl or bulk-copy the site, attempt to gain unauthorised access, interfere with the site operation, or use it for any unlawful purpose.',
          'Content you submit (reviews, photos, comments) must be your own work, lawful, and not offensive or misleading. You keep ownership and grant us a non-exclusive, worldwide licence to display it in connection with the sale of the product.',
          'We may remove content that breaches these terms.',
        ],
      },
      {
        heading: '13. Intellectual property',
        body: [
          `The site, its design, code, text, graphics, logos and the Maims name and marks belong to ${d.legalName} or its licensors. The full licence is set out in the Licence tab.`,
          'You may not use our name, logo or branding commercially, or in a way that suggests a partnership, without written permission.',
        ],
      },
      {
        heading: '14. Liability',
        body: [
          'Nothing in these terms limits our liability for death or personal injury caused by our negligence, for fraud, or for any liability that cannot be limited by law.',
          'Subject to that, our total liability arising from any order is limited to the amount you paid for that order.',
          'We are not liable for business or commercial losses, or for losses that were not reasonably foreseeable when the contract was formed.',
        ],
      },
      {
        heading: '15. Personal data',
        body: [
          'We process your personal data to take and deliver orders, answer your queries and meet our legal duties. Full details are in the Privacy tab.',
        ],
      },
      {
        heading: '16. Force majeure',
        body: [
          'We are not liable for failure to perform caused by events outside our reasonable control, including natural disasters, war, strikes, transport failure, epidemics or internet outages. Where this happens we will refund amounts paid for undelivered goods.',
        ],
      },
      {
        heading: '17. Governing law and disputes',
        body: [
          `These terms are governed by the laws of ${d.governingLaw}. If you are a consumer, you also keep the protection of any mandatory consumer law in your country of residence.`,
          `If something goes wrong, contact us first — most issues are resolved quickly. Unresolved disputes may be submitted to ${d.courts}. If you are a consumer in the EU, you may also use the European Commission's online dispute resolution platform.`,
        ],
      },
      {
        heading: '18. Complaints and contact',
        body: [
          `Write to ${d.supportEmail} with your order number and a description of the problem. We aim to reply within 2 business days and to resolve the issue within 10 business days.`,
          'Consumers in the UK and the EU can complain to their local consumer protection authority if we cannot resolve the matter.',
        ],
      },
      {
        heading: '19. Changes to these terms',
        body: [
          'We may update these terms to reflect changes in our business, products or the law. The version in force is the one published on this page at the time you order. Continued use of the site after a change means you accept the updated version.',
        ],
      },
      {
        heading: '20. Severability and entire agreement',
        body: [
          'If any clause is found unenforceable, the rest of these terms still apply. These terms, together with the Privacy and Licence tabs, are the entire agreement between you and us regarding the site.',
        ],
      },
    ],
  },
  {
    id: 'legal-privacy',
    tab: 'Privacy',
    title: 'Privacy Notice',
    intro: `This notice explains what personal data ${d.legalName} collects when you use ${d.domain}, why we collect it, and what rights you have. It applies to the website, our checkout, our WhatsApp ordering line and our customer support.`,
    sections: [
      {
        heading: '1. Who is responsible for your data',
        body: [
          `${d.legalName}, ${d.registeredAddress}, is the data controller. Privacy questions and data access requests: ${d.supportEmail}.`,
        ],
      },
      {
        heading: '2. Data we collect',
        bullets: [
          'Account data: username, email address, password (stored hashed), and optional profile details such as name, phone, delivery address and postal code.',
          'Order data: the items, quantities, prices, delivery address, phone number, order history and any message you attach to an order.',
          'Payment data: payment method and transaction references. Card numbers are entered on our payment provider\'s page and never reach our servers.',
          'Technical data: IP address, device and browser type, pages visited, referring page, and diagnostic logs.',
          'Communications: the content of emails, WhatsApp messages and support chats with us.',
        ],
      },
      {
        heading: '3. Why we use it and on what legal basis',
        body: [
          'To perform the contract: processing orders, taking payment, arranging delivery, handling returns and providing support.',
          'For our legitimate interests: securing the site, preventing fraud, improving products and the shopping experience, and understanding how the site is used. We balance these against your rights and privacy.',
          'With your consent: marketing emails, and optional cookies or analytics where our cookie banner asks for it. You can withdraw consent at any time.',
          'To meet a legal obligation: tax and accounting records, consumer guarantees and responding to lawful requests.',
        ],
      },
      {
        heading: '4. Sharing your data',
        body: [
          'We share only what is necessary with: our payment processor (Stripe, PayPal, bank transfer partners), the shipping carrier that delivers your parcel, our hosting and email providers, and our analytics provider.',
          'These providers act on our instructions and are required to protect your data. We do not sell or rent your personal data.',
          'We may disclose information where required by law, or to protect the rights, property or safety of us, our customers or others.',
        ],
      },
      {
        heading: '5. International transfers',
        body: [
          'Some providers are based outside your country, so your data is transferred abroad. Where that happens we use recognised safeguards such as adequacy decisions or standard contractual clauses.',
        ],
      },
      {
        heading: '6. Cookies',
        body: [
          'Strictly necessary cookies keep the session, currency preference and shopping cart working. These cannot be switched off.',
          'Optional analytics or advertising cookies are used only if you accept them, and you can change your choice at any time in your browser or via our cookie settings.',
          'You can also delete or block cookies in your browser settings; some features may then not work.',
        ],
      },
      {
        heading: '7. How long we keep it',
        body: [
          'Account data is kept while your account is active. Order and invoice records are kept for the period required by tax and consumer law. Marketing data is kept until you unsubscribe or withdraw consent. Technical logs are kept for a short period for security purposes.',
        ],
      },
      {
        heading: '8. Your rights',
        body: [
          'Where the GDPR or an equivalent law applies, you may ask us to confirm whether we process your data, give you a copy, correct inaccuracies, delete data, restrict or object to processing, or transfer it to another provider.',
          'You may withdraw consent for marketing at any time using the unsubscribe link in any email, or by contacting us.',
          'We answer requests within 30 days. If you are unhappy, you may complain to your local data protection authority.',
        ],
      },
      {
        heading: '9. Security',
        body: [
          'We use HTTPS in transit, hashed passwords, access controls and restricted staff access. No method of transmission or storage is completely secure, so we cannot guarantee absolute security.',
        ],
      },
      {
        heading: '10. Children',
        body: [
          'The site is not intended for children under 16, and we do not knowingly collect data from them. If you believe a child has provided data, contact us and we will delete it.',
        ],
      },
      {
        heading: '11. Changes to this notice',
        body: [
          'We update this notice when our processing changes. The date at the top of this page shows the current version, and material changes are announced on the site or by email.',
        ],
      },
    ],
  },
  {
    id: 'legal-licence',
    tab: 'Licence',
    title: 'Site Licence and Content Licence',
    intro: `This licence sets out what you may and may not do with ${d.domain}, its content, its design and its brand. By using the site you accept it.`,
    sections: [
      {
        heading: '1. Ownership',
        body: [
          `All content on ${d.domain} — including the layout, code, text, product copy, photographs, illustrations, graphics, logos, icons, the Maims name and all trade marks — is owned by ${d.legalName} or its licensors, and is protected by copyright, design, trade mark and other intellectual property laws.`,
        ],
      },
      {
        heading: '2. Licence granted to you',
        body: [
          'We grant you a personal, non-exclusive, non-transferable, revocable, royalty-free licence to browse the site and to download or print one copy of any page for your own private, non-commercial use.',
          'You may share a link to any page of the site, and quote short extracts with clear attribution.',
        ],
      },
      {
        heading: '3. What is not permitted',
        bullets: [
          'Copying, republishing or reposting substantial parts of the site, whether manually, by scraping or by using automated tools such as robots, crawlers or AI training bots.',
          'Using our content commercially, including reselling, repackaging or including it in a product, course, dataset or model.',
          'Removing or altering copyright notices, watermarks, attribution or source credits.',
          'Using our name, logo, brand colours or look-and-feel in a way that implies endorsement, partnership or affiliation without written permission.',
          'Reverse engineering, decompiling or attempting to derive source code from the site, except where that restriction is not permitted by law.',
          'Overloading the site, probing it for vulnerabilities without permission, or bypassing security, rate limits or access controls.',
        ],
      },
      {
        heading: '4. Product images and descriptions',
        body: [
          'You may use a product image or description in a review, article or social post that is not written for commercial gain, provided you link back to the product page and do not crop out or alter the brand marks.',
          'Rights in model, photographer and designer imagery on the site remain with the people who created them. Requests to use an image for advertising must go to support and require written permission.',
        ],
      },
      {
        heading: '5. Third-party links and content',
        body: [
          'The site may link to third-party websites, payment providers and social platforms. We do not control them and are not responsible for their content, availability or privacy practices.',
          'Third-party content is used under the terms set by its owner and remains their property.',
        ],
      },
      {
        heading: '6. Content you submit',
        body: [
          'When you post a review, photo or other content, you confirm it is your own, accurate, and not unlawful or offensive.',
          'You keep ownership of it and grant us a worldwide, non-exclusive, royalty-free, transferable licence to host, display, distribute and use it to operate and promote the site and sell the product it refers to. This licence survives deletion of the content.',
        ],
      },
      {
        heading: '7. Feedback',
        body: [
          'If you send us suggestions or ideas about the site or the products, you allow us to use them freely and without paying you, and you confirm you have the right to share them.',
        ],
      },
      {
        heading: '8. Software and open source',
        body: [
          'The site is built with open source software, which remains governed by its own licences. Nothing in this document restricts rights that those licences grant you.',
        ],
      },
      {
        heading: '9. Complaints and takedowns',
        body: [
          `If you believe content on the site infringes your copyright or other rights, or is unlawful, email ${d.supportEmail} with the page URL, the right you are relying on and your contact details. We will review the request and remove or restrict the content where appropriate.`,
        ],
      },
      {
        heading: '10. Changes and termination',
        body: [
          'We may update, rebrand or withdraw parts of the site at any time. We may suspend or terminate access to anyone who breaches this licence.',
          'Sections that by their nature should survive termination — ownership, disclaimers, liability limits and governing law — remain in effect afterwards.',
        ],
      },
    ],
  },
]

/** Small print shown under the tabs. */
export const LEGAL_NOTICE = {
  acceptance: `By placing an order or creating an account on ${d.domain} you confirm that you have read and accepted these Terms & Conditions, the Privacy Notice and the Site Licence.`,
  disclaimer: 'This summary is provided for convenience. The full terms above apply, and the version published on this page at the time of your order is the version that governs your purchase.',
  contact: `Questions? Email ${d.supportEmail} and we will get back to you within 2 business days.`,
}
