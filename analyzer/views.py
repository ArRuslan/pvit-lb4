from uuid import uuid4

from axe_selenium_python import Axe
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.shortcuts import render, redirect
from django.urls import reverse
from selenium import webdriver
from selenium.webdriver.firefox.options import Options as FirefoxOptions

from .forms import URLForm, RegisterForm
from .models import Violation, WebsiteScan


def register_view(request):
    if request.method == "POST":
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect("url_check")
    else:
        form = RegisterForm()
    return render(request, "registration/register.html", {"form": form})


@login_required
def url_check_view(request):
    if request.method == "POST":
        form = URLForm(request.POST)
        if not form.is_valid():
            return render(request, "check_form.html", {"form": form})

        url = form.cleaned_data["url"]

        options = FirefoxOptions()
        options.headless = True
        options.add_argument("--headless")
        options.add_argument("--log-level=3")
        driver = webdriver.Firefox(options=options)
        driver.get(url)
        driver.set_window_size(1280, 720)

        axe = Axe(driver)
        axe.inject()
        results = axe.run()

        screenshot = driver.get_screenshot_as_png()

        driver.quit()

        scan = WebsiteScan.objects.create(url=url, user=request.user)
        scan.screenshot.save(f"{uuid4()}.png", ContentFile(screenshot), save=True)

        for v in results["violations"]:
            for node in v["nodes"]:
                Violation.objects.create(
                    scan=scan,
                    violation_id=v["id"],
                    impact=v.get("impact"),
                    description=v["description"],
                    help_text=v["help"],
                    help_url=v["helpUrl"],
                    failure_summary=node.get("failureSummary", ""),
                    html_snippet=node.get("html", "")
                )

        return redirect(f"{reverse('results')}?scan_id={scan.id}")
    else:
        form = URLForm()

    return render(request, "check_form.html", {"form": form})


@login_required
def results_view(request):
    scan_id = request.GET.get("scan_id")
    scan = WebsiteScan.objects.get(id=scan_id)
    violations = scan.violations.all()

    return render(request, "results.html", {
        "violations": violations,
        "scan": scan,
    })
