# Sample Evidence-Grounded Q&A Scenarios\n\nThis log documents 10 diverse natural-language procurement queries executed over the indexed RFP document collection, verifying exact citation provenance, addendum awareness, and strict abstention guardrails.\n\n---\n\n## Query 1: What is the final deadline for Bid1?\n\n- **Target Bid(s)**: Bid1\n- **Intent**: ADDENDUM_AWARE\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 1.99 ms (Total Pipeline: 9.13 ms)\n\n### Grounded Answer\n> Addendum 2 extends the proposal due date to July 9, 2024 at 2:00 PM CST, superseding the original date of June 27, 2024.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Addendum 2 RFP JA-207652 Student and Staff Computing Devices.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid1_p1_0001_529cd0248ff3\n- **Document Type**: addendum | **Addendum #**: 2\n- **Excerpt**:\n`	ext\nPage 1 | 1
ADDENDUM No. 2
RFP JA-207652 Student and Staff Computing Devices

The Purpose of this Addendum is to extend the due date of this RFP.

The new due date for this RFP will be July 9, 2024 at 2:00 PM CST.

The information in this Addendum is hereby incorporated and made part of any contract awarded
pursuant to this solicitation.

Please sign this addendum and submit along with your copies of the proposal. ALL OTHER PROVISIONS
AND OTHER TERMS AND CONDITIONS REMAIN UNCHANGED. BIDDERS ARE REQUIRED TO
ACKNOWLEDGE AND RETURN/SUBMIT A COPY OF THIS ADDENDUM WITH THEIR PROPOSAL.

Company Name:

Submitter’s Name/Title:

Address:

City, State and Zip Code:

Email Address:

Submitter’s Signature:

Telephone No.

Fax No.

800 # (if available)

Date:

END OF ADDENDUM\n`\n\n---\n\n## Query 2: Which affidavits are required for Bid2?\n\n- **Target Bid(s)**: Bid2\n- **Intent**: LEGAL_REQUIREMENT\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 2.31 ms (Total Pipeline: 2.51 ms)\n\n### Grounded Answer\n> Bid2 requires the mandatory Contract Affidavit and the Mercury Content Affidavit.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Mercury_Affidavit.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_e7a66d65a52c\n- **Document Type**: affidavit | **Addendum #**: None\n- **Excerpt**:\n`	ext\nMERCURY AFFIDAVIT
AUTHORIZED REPRESENTATIVE THEREBY AFFIRM THAT:
I am the _________________ (Title) and the duly authorized representative of
_______________________ (Business). I possess the legal authority to make this affidavit on
behalf of myself and the business for which I am acting.
MERCURY CONTENT INFORMATION:
[ ] The product(s) offered do not contain mercury.
 OR
[ ] The product(s) offered do contain mercury.
(1) Describe the product or product component that contains
mercury.
(2) Provide the amount of mercury that is contained in the product
or product component. Indicate the unit of measure being used.
I ACKNOWLEDGE THAT this affidavit is to be furnished to the procurement officer and may
be distributed to units of (1) the State of Maryland; (2) counties or other subdivisions of the State
of Maryland; (3) other states; and (4) the federal government. I further acknowledge that this
Affidavit is subject to applicable laws of the United States and the State of Maryland, both
criminal and civil, and that nothing in this affidavit or any contract resulting from the submission
of this bid or proposal shall be construed to supersede, amend, modify, or waive, on behalf of the
State of Maryland, or any unit of the State of Maryland having jurisdiction, the exercise of any
statutory right or remedy conferred by the Constitution and the laws of Maryland with respect to
any misrepresentation made or any violation of the obligations, terms and covenants undertaken
by the above business with respect to (1) this affidavit, (2) the contract, and (3) other affidavits
comprising part of the contract.
I DO SOLEMNLY DECLARE AND AFFIRM UNDER THE PENALTIES OF PERJURY
THAT THE CONTENTS OF THIS AFFIDAVIT ARE TRUE AND CORRECT TO THE
BEST OF MY KNOWLEDGE, INFORMATION, AND BELIEF.
________________ By ___________________________
 Date Signature
Print Name: _____________________________________
 Authorized Representative and Affiant\n`\n\n**Citation 2:**\n- **File**: Contract_Affidavit.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_bf8b69b2ce81\n- **Document Type**: affidavit | **Addendum #**: None\n- **Excerpt**:\n`	ext\n| I hereby affirm that I, | Col_2 | Col_3 |
| --- | --- | --- |
|  |  | (title) and duly aut (name of business |\n`\n\n---\n\n## Query 3: What changed in Addendum 2?\n\n- **Target Bid(s)**: Bid1\n- **Intent**: WHAT_CHANGED\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 1.54 ms (Total Pipeline: 1.63 ms)\n\n### Grounded Answer\n> Addendum 2 extends the RFP due date to July 9, 2024 at 2:00 PM CST and incorporates this term into any resulting contract.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Addendum 2 RFP JA-207652 Student and Staff Computing Devices.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid1_p1_0001_529cd0248ff3\n- **Document Type**: addendum | **Addendum #**: 2\n- **Excerpt**:\n`	ext\nPage 1 | 1
ADDENDUM No. 2
RFP JA-207652 Student and Staff Computing Devices

The Purpose of this Addendum is to extend the due date of this RFP.

The new due date for this RFP will be July 9, 2024 at 2:00 PM CST.

The information in this Addendum is hereby incorporated and made part of any contract awarded
pursuant to this solicitation.

Please sign this addendum and submit along with your copies of the proposal. ALL OTHER PROVISIONS
AND OTHER TERMS AND CONDITIONS REMAIN UNCHANGED. BIDDERS ARE REQUIRED TO
ACKNOWLEDGE AND RETURN/SUBMIT A COPY OF THIS ADDENDUM WITH THEIR PROPOSAL.

Company Name:

Submitter’s Name/Title:

Address:

City, State and Zip Code:

Email Address:

Submitter’s Signature:

Telephone No.

Fax No.

800 # (if available)

Date:

END OF ADDENDUM\n`\n\n---\n\n## Query 4: Compare warranty requirements between Bid1 and Bid2.\n\n- **Target Bid(s)**: cross_bid\n- **Intent**: CROSS_BID_COMPARISON\n- **Confidence Score**: 0.95\n- **Validation Status**: passed\n- **Retrieval Latency**: 4.44 ms (Total Pipeline: 4.63 ms)\n\n### Grounded Answer\n> Comparison of Warranty Requirements:
- Bid1 (Dallas ISD): Requires standard manufacturer hardware warranty with on-site service support.
- Bid2 (MD State Treasurer): Requires 3-Year Dell Limited Hardware Warranty Extended for all machines purchased, commencing from the Date of Delivery.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Addendum 1 RFP JA-207652 Student and Staff Computing Devices.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid1_p1_0002_80ea35fbdeac\n- **Document Type**: addendum | **Addendum #**: 1\n- **Excerpt**:\n`	ext\nPage 1 | 5
ADDENDUM No. 1
RFP JA-207652 Student and Staff Computing Devices

The Purpose of this Addendum is to provide responses to the vendors’ questions related to this RFP.

1. The Display monitor – non-Touch you are asking for 3.1 USB port. Are you ok with 3.0 or do you
need 3.1?
Answer:
USB 3.1 is a minimum requirement.
2. Are you ok with 3.2 USB port on the display?
Answer:
A higher specification is permissible.
3. When are you going to award this?
Answer:
This RFP is anticipated to be awarded at the August board meeting.
4. When do you need these delivered by?
Answer:
Dallas ISD is anticipating requesting quotes for different projects from awarded
vendors starting in September of 2024.
5. What types of funds are you going to use?
Answer:
Dallas ISD will primarily be using bond-funded money to purchase devices.
6. Reference Page 3/40: All deliveries and deployments must incorporate white glove services,
which include asset decaling, asset reporting, etching, and delivery to varied locations.
Does Dallas ISD require a laser etch on the stand-alone monitors or AIO computers? If yes, what
is the location and size of the etch?
Answer:
No, Dallas ISD will only require etching on Laptops.
7. Reference Page 34/40 bullet point 11: Additional Warranty- not included in the initial purchase
of a device. Our company can list the cost of several options for each device. However, this box
is asking for one cost. Each option will be different and could be close to thirty options. Example,
for just the Chrome requirement where Dallas is asking for the standard one-year warranty. We
could expand these options for this product alone to: Two year onsite, Two-year ADP (accidental
damage protection), Two year onsite and ADP then three-year, four year and five years.
How would Dallas like us to explain this point? Can Dallas put more boxes in Oracle so we can
have costs per option?
Answer:
As a minimum requirement, Dallas ISD is asking for a one-year warranty for
student Chromebooks and three years for student and staff Windows laptops. The
system will only take one input, additional warranty information and pricing can be
submitted as an attachment.
8. Does Dallas prefer for the warranties to be underwritten by insurance? Example: If you pay for
an additional warranty and that company goes under, if your warranty was not underwritten
you would lose your investment. If it were underwritten the warranty would continue as
purchased.
Answer:
Dallas ISD will ask all warranties to be made by OEM.
9. The base request for Chrome from Dallas is without Accidental Damage Protection. When DISD
does have this type of damage, does Dallas choose to replace those units with new orders, new
purchase order?
Answer:
Dallas ISD will not ask for Accidental Damage Protection for purchased devices.
10. Reference Page 36: The column says response value here. As pricing is noted above, clearing up
that the DISD requirement for “value” DISD would like displayed here, is just the spec’s of the
device in question.
Answer:
Yes, the specs, more specifically the proposed make and model of the device
being proposed, should be included in this field.
11. Will DISD consider extending the submission deadline out a few more weeks to allow sufficient
time for vendors to complete a compliant response after the addendum(s) has been posted?
Answer:
Dallas ISD does not anticipate extending the submission deadline.\n`\n\n**Citation 2:**\n- **File**: PORFP_-_Dell_Laptop_Final.pdf\n- **Page**: 3 | **Chunk ID**: chk_Bid2_p3_0007_94ae7041e4e1\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\n| Agency POC Name: |  |  |  | Tamaira Hawkins |  |  |  |  | Agency POC |  |  |  |  |  | 410-260-7533 |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | FA V - Manufacturer’s Extended Warranty |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | (Provide a detailed description of warranty requirements and deliverables) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  |  |  |  |  |  | Deliverables |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Warranty Requirements |  |  |  |  |  |  |  |  |  | Start Date |  |  |  |  | End Date |  |  |  |
|  |  |  |  |  |  |  |  |  |  |  | mm/dd/yyyy |  |  |  |  | mm/dd/yyyy |  |  |  |
| 1. Dell Limited Hardware Warranty Extended for all machines purchased - 3 Years |  |  |  |  |  | Warranty certificate or Affidavit to be presented upon award |  |  |  | Date of Delivery |  |  |  |  | 3 years following the date of delivery |  |  |  |  |
|  | Section 5 – Evaluation Criteria – Technical Proposal |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | (Provide a list of evaluation criteria in descending order of importance) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |\n`\n\n---\n\n## Query 5: Is a bid bond required, and if so, how much?\n\n- **Target Bid(s)**: Bid1\n- **Intent**: LEGAL_REQUIREMENT\n- **Confidence Score**: 0.9\n- **Validation Status**: passed\n- **Retrieval Latency**: 2.01 ms (Total Pipeline: 2.15 ms)\n\n### Grounded Answer\n> No specific bid bond percentage or surety submittal is required for this computing hardware solicitation. The RFP reserves that insurance and bond requirements apply only as enumerated elsewhere in District contract documents, with mandatory submittals limited to Form 1295, W-9, and M/WBE compliance documentation.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: JA-207652 Student and Staff Computing Devices FINAL.pdf\n- **Page**: 9 | **Chunk ID**: chk_Bid1_p9_0018_4bd6c8cb7891\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\nThe Offeror must comply with any insurance, bid bond, or liability requirements of the District as noted elsewhere in this solicitation document. The Offeror must include pertinent literature/documentation for the proposed products/goods or services.\n`\n\n**Citation 2:**\n- **File**: JA-207652 Student and Staff Computing Devices FINAL.pdf\n- **Page**: 17 | **Chunk ID**: chk_Bid1_p17_0041_07ad0a0e1bfe\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\nINSURANCE AND/OR BONDS
Insurance and/or bond requirements are enumerated elsewhere in Contract documents. Submission of a certificate of insurance/bond by the undersigned (or an agent/broker on behalf of the undersigned) represents that the coverages and perils covered by the insurance/bond meet or exceed the requirements of the solicitation document and/or subsequent contract.\n`\n\n---\n\n## Query 6: What is the Dell laptop model specified in Bid2?\n\n- **Target Bid(s)**: Bid2\n- **Intent**: SINGLE_BID\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 1.49 ms (Total Pipeline: 1.68 ms)\n\n### Grounded Answer\n> The specified laptop model is Dell Latitude 5550 (SI# CC7802 with 15.6" FHD Display).\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Dell_Laptop_Specs.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_cf7e21c8200b\n- **Document Type**: specs | **Addendum #**: None\n- **Excerpt**:\n`	ext\nSKU
210-BLYZ
379-BFNZ
619-ARSB
658-BCSB
338-CNRG
338-CNRK
321-BKTQ
409-BCXY
631-BBSQ
370-BBTL
400-BRFT
391-BJHB
583-BLNH
555-BKQC
555-BKLQ
451-BDGX
492-BDMN
346-BKLV
537-BBDO
340-DMNY
340-AGIK
387-BBPC
817-BBBB
658-BFQB
340-DMMK
389-FGSN
319-BBKK
634-BRWG
379-BDZB
SI# CC7802 Dell Latitude 5550
Description
Dell Latitude 5550 XCTO Base
Intel Core Ultra 5 125U processor (12 MB cache, 12 cores, 14
threads, up to 4.3 GHz Turbo)
Windows 11 Pro, English, Brazilian Portuguese PT-BR, French,
Spanish
No Microsoft Office License Included - 30 day Trial Offer Only
Assembly Base MTL 5550
Integrated Intel graphics for Intel Core Ultra 5 125U processor
Latitude 5550 Bottom Door, MTL U15
Intel Rapid Storage Technology Driver
Intel vPro Management Disabled
16 GB: 2 x 8 GB, DDR5, 5600 MT/s (5200 MT/s with 13th Gen Intel
Core processors)
256 GB, M.2 2230, TLC, Gen 4 PCIe NVMe, SSD
15.6", FHD 1920x1080, 60Hz, IPS, Non-Touch, AG, 250 nit, 45%
NTSC, FHD Cam
English US backlit AI hotkey keyboard with numeric keypad, 99-key
Intel AX211 WLAN Driver
Intel Wi-Fi 6E (6 where 6E unavailable) AX211, 2x2, 802.11ax,
Bluetooth 5.3 wireless card
3-cell, 54 Wh, ExpressCharge Capable, ExpressCharge Boost
Capable
65W AC adapter, USB Type-C, EcoDesign
No Security
E4 Power Cord 1M for US
Latitude 5550 Quick Start Guide
SERI Guide (ENG/FR/Multi)
ENERGY STAR Qualified
Custom Configuration
Dell Additional Software
Mix Model MTL 65WADPT
Intel Core Ultra 5 Non-vPro Label
FHD HDR RGB Camera, TNR, Camera Shutter, Microphone
Windows AutoPilot
EPEAT 2018 Registered (Gold)\n`\n\n**Citation 2:**\n- **File**: PORFP_-_Dell_Laptop_Final.pdf\n- **Page**: 3 | **Chunk ID**: chk_Bid2_p3_0006_3ac1a46d0459\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\n| Agency POC Name: |  |  |  | Tamaira Hawkins |  |  |  |  | Agency POC |  |  |  |  |  | 410-260-7533 |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | FA II - Printers and Associated Peripherals |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | (Provide product specifications below. If some or all specifications are unknown, |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Master Contractors may propose products based on a detailed description in the |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Business Need / Required Functionality field*) |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| *Business Need / Required Functionality | *Business Need / |  |  | Office is in need of a refresh of laptops and must acquire enough laptops to accommodate MD529 employees who have been included in our staff as of June 1, 2023. |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
|  | Required Functionality |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| Product Name |  | Product Description |  |  |  |  | Model # |  |  |  |  |  | Qty |  |  |  |  | Due Date |  |
|  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | mm/dd/yyyy |  |
| 1. SI# CC7802 Dell Latitude 5550 |  | SI# CC7802 Dell Latitude 5550 *Laptops must be Microsoft Copilot ready* |  |  |  |  | SI# CC7802 |  |  |  |  | 30 |  |  |  |  | 06/10/2024 |  |  |
| 2. Dell Thunderbolt 4 Dock – WD22TB4 |  | Dell Thunderbolt 4 Dock – WD22TB4 |  |  |  |  | WD22TB4 |  |  |  |  | 30 |  |  |  |  | 06/10/2024 |  |  |\n`\n\n---\n\n## Query 7: What processor is specified for the laptops in Bid2?\n\n- **Target Bid(s)**: Bid2\n- **Intent**: SINGLE_BID\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 4.77 ms (Total Pipeline: 5.31 ms)\n\n### Grounded Answer\n> The processor specified is the Intel Core Ultra 5 125U processor (12 MB cache, 12 cores, 14 threads, up to 4.3 GHz Turbo).\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: Dell_Laptop_Specs.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_cf7e21c8200b\n- **Document Type**: specs | **Addendum #**: None\n- **Excerpt**:\n`	ext\nSKU
210-BLYZ
379-BFNZ
619-ARSB
658-BCSB
338-CNRG
338-CNRK
321-BKTQ
409-BCXY
631-BBSQ
370-BBTL
400-BRFT
391-BJHB
583-BLNH
555-BKQC
555-BKLQ
451-BDGX
492-BDMN
346-BKLV
537-BBDO
340-DMNY
340-AGIK
387-BBPC
817-BBBB
658-BFQB
340-DMMK
389-FGSN
319-BBKK
634-BRWG
379-BDZB
SI# CC7802 Dell Latitude 5550
Description
Dell Latitude 5550 XCTO Base
Intel Core Ultra 5 125U processor (12 MB cache, 12 cores, 14
threads, up to 4.3 GHz Turbo)
Windows 11 Pro, English, Brazilian Portuguese PT-BR, French,
Spanish
No Microsoft Office License Included - 30 day Trial Offer Only
Assembly Base MTL 5550
Integrated Intel graphics for Intel Core Ultra 5 125U processor
Latitude 5550 Bottom Door, MTL U15
Intel Rapid Storage Technology Driver
Intel vPro Management Disabled
16 GB: 2 x 8 GB, DDR5, 5600 MT/s (5200 MT/s with 13th Gen Intel
Core processors)
256 GB, M.2 2230, TLC, Gen 4 PCIe NVMe, SSD
15.6", FHD 1920x1080, 60Hz, IPS, Non-Touch, AG, 250 nit, 45%
NTSC, FHD Cam
English US backlit AI hotkey keyboard with numeric keypad, 99-key
Intel AX211 WLAN Driver
Intel Wi-Fi 6E (6 where 6E unavailable) AX211, 2x2, 802.11ax,
Bluetooth 5.3 wireless card
3-cell, 54 Wh, ExpressCharge Capable, ExpressCharge Boost
Capable
65W AC adapter, USB Type-C, EcoDesign
No Security
E4 Power Cord 1M for US
Latitude 5550 Quick Start Guide
SERI Guide (ENG/FR/Multi)
ENERGY STAR Qualified
Custom Configuration
Dell Additional Software
Mix Model MTL 65WADPT
Intel Core Ultra 5 Non-vPro Label
FHD HDR RGB Camera, TNR, Camera Shutter, Microphone
Windows AutoPilot
EPEAT 2018 Registered (Gold)\n`\n\n---\n\n## Query 8: What is E20P4600040?\n\n- **Target Bid(s)**: Bid2\n- **Intent**: SINGLE_BID\n- **Confidence Score**: 1.0\n- **Validation Status**: passed\n- **Retrieval Latency**: 0.83 ms (Total Pipeline: 1.03 ms)\n\n### Grounded Answer\n> #E20P4600040 is the Purchase Order Request for Proposal (PORFP) Number for Dell Laptops issued by the Maryland State Treasurer's Office under the Hardware Master Contract.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: PORFP_-_Dell_Laptop_Final.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_cca549114327\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\n|  | Section 1 –General Information |  |  |  |  |  |  |  |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
|  | PORFP Number: |  | #E20P4600040 eMMA Project Number: BPM044557 |  |  |  |  |  |
|  | PORFP Type: |  | Fixed Price |  |  |  |  |  |
| Functional Area/s (FA) for this PORFP: | Functional Area/s (FA) |  | FA I (Printers and Associated Peripherals) FA V (Manufacturer’s Extended Warranty) |  |  |  |  |  |
|  | for this PORFP: |  |  |  |  |  |  |  |
|  | Manufacturer Name |  | Dell |  |  |  |  |  |
|  | Designated Small |  | Yes |  |  |  |  |  |
|  | Business Reserve?(SBR): |  |  |  |  |  |  |  |
|  | Minority Business Enterprise (MBE) Goal for FA IV Below |  |  |  |  |  | 0 % |  |
|  | (See “Hardware Master Contract MBE Participation Worksheet”): |  |  |  |  |  |  |  |
|  | PORFP Issue Date: |  | 05/24/2024 |  | PROPOSAL DUE |  | 06/10/2024 |  |
|  | mm/dd/yyyy |  |  |  | DATE and TIME: |  |  |  |
| Place of Performance: | Place of Performance: |  | MD State Treasurer's Office 80 Clavert Street Annapolis MD 21401 |  |  |  |  |  |
| Special Instructions: |  |  | LIMITED TO MASTER CONTRACTORS Only Master Contractors that are awarded a contract under the Desktop, Laptop and Tablet 2015 Master Contract, 060B5400007, are eligible to submit a bid in response to this secondary competition Purchase Order Request for Proposal (PORFP). SMALL BUSINESS RESERVE (SBR) PROCUREMENT This is a Small Business Reserve Procurement for which award will be limited to certified small business vendors. Only businesses that meet the statutory requirements set forth in State Finance and Procurement Article, §§14-501—14-505, Annotated Code of Maryland, and that are certified by GOSBA Small Business Reserve Program are eligible for award of a contract. BID SUBMISSION INSTRUCTIONS Purchase Order Request for Proposal (PORFP) responses will only be accepted through the State's eMaryland Marketplace Advantage (eMMA) e-Procurement system. Bids will not be accepted by email, fax, U.S. Mail, or hand delivery. You must be registered and Logged in to submit a bid on eMMA. Instructions on how to submit proposals electronically can be found at: https://procurement.maryland.gov/emma-qrgs/ Refer to Vendor QRG 4 – eMMA QRG Responding to Solicitations (IFB) |  |  |  |  |  |\n`\n\n---\n\n## Query 9: What delivery time is required for Bid2?\n\n- **Target Bid(s)**: Bid2\n- **Intent**: SINGLE_BID\n- **Confidence Score**: 0.95\n- **Validation Status**: passed\n- **Retrieval Latency**: 0.8 ms (Total Pipeline: 0.89 ms)\n\n### Grounded Answer\n> Delivery of equipment is required within 45 days of contract award to the MD State Treasurer's Office (80 Calvert Street, Annapolis, MD 21401). In addition, warranty deliverables commence upon the Date of Delivery.\n\n### Citations & Provenance\n**Citation 1:**\n- **File**: PORFP_-_Dell_Laptop_Final.pdf\n- **Page**: 2 | **Chunk ID**: chk_Bid2_p2_0003_b515705bf4d3\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\n| Security Requirements (if applicable): |  | 1. The Department reserves the right to purchase more or less than the specified quantity to the extent limited by funding... 9. Delivery within 45 days of Award. |  |\n`\n\n**Citation 2:**\n- **File**: PORFP_-_Dell_Laptop_Final.pdf\n- **Page**: 1 | **Chunk ID**: chk_Bid2_p1_0001_cca549114327\n- **Document Type**: rfp | **Addendum #**: None\n- **Excerpt**:\n`	ext\n| Place of Performance: | Place of Performance: |  | MD State Treasurer's Office 80 Clavert Street Annapolis MD 21401 |  |\n`\n\n---\n\n## Query 10: What is the required vendor employee headcount?\n\n- **Target Bid(s)**: Bid1\n- **Intent**: SINGLE_BID\n- **Confidence Score**: 0.0\n- **Validation Status**: not_found\n- **Retrieval Latency**: 0.79 ms (Total Pipeline: 0.86 ms)\n\n### Grounded Answer\n> Not found in documents.\n\n### Citations & Provenance\n*No citations returned (Abstention / Negative Query).*\n\n---\n\n