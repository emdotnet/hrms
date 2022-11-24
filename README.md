# HR Management System

## :hammer_and_wrench: How the HR Management System directory works

Open Source, modern, and easy-to-use HR and Payroll Software for all organizations.
Based on [Frappe HR](https://github.com/frappe/hrms)

Dokos HRMS offers over 13 different modules from Employee Management to Onboarding, Leaves, Payroll or Taxation.

> Warning: Some functionalities may not be applicable for all countries

![HRMS](hrms.png)

### Key Features

- Employee Management
- Employee Lifecycle
- Leave and Attendance
- Shift Management
- Expense Claims and Advances
- Hiring
- Performance Management
- Fleet Management
- Training
- Payroll
- Taxation
- Compensation
- Analytics

## :rocket: Dokos project

Dokos is a 100% open-source management software that is based on ERPNext.

It is distributed under the GPLv3 license.

The 100% web architecture of Dokos allows you to use it in a public cloud as well as in a private cloud.

You can install it on your own servers.

The Dodock framework on which Dokos is installed also allows the installation of other applications. You can thus develop your own customizations, host them on your server and make them evolve in parallel with Dokos, without modifying its source code.

## :books: Use and documentation

#### Installation and use :construction:

##### 1. Installation

1. [Install Dokos Cli and Dodock](https://doc.dokos.io/fr/getting-started).
2. [Install Dokos](https://gitlab.com/dokos/dokos).
3. Once Dokos is installed, add the HRMS application to your bench by running

    ```sh
    $ bench get-app hrms --branch <version branch>
    ```

> Example: If you want to use this application with Dokos v3, you should use branch `v3.x.x`  
> `$ bench get-app hrms --branch v3.x.x`

4. After that, you can install the hrms app on the required site by running
    ```sh
    $ bench --site sitename install-app hrms
    ```

##### 2. Documentation to set up HRMS : [HRMS documentation](https://doc.dokos.io/fr/human-resources)

##### 3. Access to the Dokos community: [Forum](https://community.dokos.io/)

#### How to contribute :rocket:

**Description of the process and the branches to use**

1. I create a ticket with my proposal

- if it is for a new feature

- if a discussion is needed before making a Merge Request

2. I propose a Merge Request with my fixes/new features

3. The merge request must always be proposed on the develop branch and a retrofit request must be made in the merge request description

4. The merge request must contain a complete description and possibly screenshots

5. If a documentation is needed, it must be created on the wiki before the Merge Request is sent for validation

:point_right: Link to submit a ticket: **[Here](https://gitlab.com/dokos/dokos/-/issues)**

### :link: Useful links

- Detailed documentation: [doc.dokos.io](https://doc.dokos.io/fr/home)

- Community forum: [community.dokos.io](https://community.dokos.io/)

- Youtube channel: [Dokos Youtube](https://www.youtube.com/channel/UC2f3m8QANAVfKi2Pzw2fBlw)

- The Facebook page: [Dokos Facebook](https://www.facebook.com/dokos.io)

- The Linkedin page: [Dokos Linkedin](https://www.linkedin.com/company/dokos.io)

### :grey_question: Others informations

#### Website :card_index_dividers:

For details and documentation, see the website

[https://dokos.io](https://dokos.io)

## License

GNU GPL V3. (See [license.txt](license.txt) for more information).

The HRMS code is licensed as GNU General Public License (v3) and the copyright is owned by Frappe Technologies Pvt Ltd (Frappe), Dokos SAS and Contributors.

#### Publisher :pushpin:

Dokos SAS
